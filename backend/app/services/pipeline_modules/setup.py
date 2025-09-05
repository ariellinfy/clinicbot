# backend/app/services/pipeline_modules/setup.py
from typing import Dict, Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain.chains import create_sql_query_chain, RetrievalQA
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from ...models.types import IntentOut, RouteOutput
from ...utils.config import LLM_MODEL, OPENAI_EMBED_MODEL, SQL_DB_URL
from ...utils.vectorstore import get_retriever, set_embedding_api_key
from ...utils.rules import INTENT_PROMPT, SQL_PROMPT, ROUTER_PROMPT, GENERATION_PROMPT
from ...utils.logging import get_logger

logger = get_logger(__name__)

# ----- API readiness flag -----
_API_READY: bool = False

def api_is_ready() -> bool:
    return _API_READY

# ----- Lazy-initialized globals (no env key usage) -----
llm: Optional[ChatOpenAI] = None
sql_chain = None
execute_sql = None
retriever = None
knowledge_chain = None
intent_chain = None
router = None
generation_chain = None
generator_with_history: Optional[RunnableWithMessageHistory] = None

# SQL DB (safe to init without key)
db = SQLDatabase.from_uri(SQL_DB_URL)
execute_sql = QuerySQLDatabaseTool(db=db)

# Session store
SESSION_STORE: Dict[str, InMemoryChatMessageHistory] = {}
def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    hist = SESSION_STORE.get(session_id)
    if hist is None:
        hist = InMemoryChatMessageHistory()
        SESSION_STORE[session_id] = hist
    return hist

def clear_session(session_id: str):
    SESSION_STORE.pop(session_id, None)

# Router
def parse_router(json_str: str) -> RouteOutput:
    import json
    try:
        obj = json.loads(json_str)
        return RouteOutput(obj.get("route","both"), float(obj.get("confidence",0.0)))
    except Exception:
        return RouteOutput("both", 0.0)
    
def set_openai_key(new_key: str) -> bool:
    """
    Validate the key cheaply, then rebuild LLM + chains and set embeddings key.
    """
    global llm, sql_chain, knowledge_chain, intent_chain, generation_chain, generator_with_history, retriever, router, _API_READY

    if not new_key or not isinstance(new_key, str):
        return False

    # 1) Validate with a tiny embeddings call (cheapest reliable check)
    try:
        OpenAIEmbeddings(api_key=new_key, model=OPENAI_EMBED_MODEL).embed_query("ok")
    except Exception:
        return False  # invalid key or blocked

    # 2) Swap LLM
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.2, api_key=new_key)

    # 3) Swap embeddings used by retriever
    set_embedding_api_key(new_key)  # same model; if you change models, re-ingest

    # 4) Rebuild chains
    sql_chain = create_sql_query_chain(llm=llm, db=db, prompt=SQL_PROMPT, k=5)
    retriever = get_retriever(k=4)
    knowledge_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
    intent_chain = INTENT_PROMPT | llm.with_structured_output(IntentOut)
    router = ROUTER_PROMPT | llm | StrOutputParser() | RunnableLambda(parse_router)
    
    generation_chain = GENERATION_PROMPT | llm | StrOutputParser()
    generator_with_history = RunnableWithMessageHistory(
        generation_chain,
        get_session_history,
        input_messages_key="query",
        history_messages_key="chat_history",
    )
    _API_READY = True
    return True