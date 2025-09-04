from typing import Dict, Optional
from fastapi import HTTPException

from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain.chains import create_sql_query_chain, RetrievalQA
from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from .pii import detect_language, sanitize_text_for_llm, redact_text_before_return
from ..models.types import IntentOut, RouteOutput
from ..utils.config import LLM_MODEL, OPENAI_EMBED_MODEL, SQLITE_URL, JANEAPP_BASE
from ..utils.vectorstore import get_retriever, set_embedding_api_key
from ..utils.rules import INTENT_PROMPT, SQL_PROMPT, ROUTER_PROMPT, GENERATION_PROMPT, PUBLIC_REFUSAL
from ..utils.db import direct_sql_pricing_consultation, expand_query_for_clinic, get_janeapp_base

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
db = SQLDatabase.from_uri(SQLITE_URL)
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
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
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

# Queries
def run_sql(q: str):
    expanded = expand_query_for_clinic(q)
    sql = sql_chain.invoke({"question": expanded, "input": expanded, "top_k": 5})
    if not sql or not sql.strip():
        return {"ok": False, "sql": "", "rows": [], "text": ""}
    try:
        raw = execute_sql.invoke(sql)
        if isinstance(raw, (list, tuple)):
            try:
                from tabulate import tabulate
                text = tabulate(raw, headers="keys" if raw and isinstance(raw[0], dict) else [], tablefmt="github")
            except Exception:
                text = str(raw)
        else:
            text = str(raw)
        return {"ok": bool(str(text).strip()), "sql": sql, "rows": raw, "text": text}
    except Exception:
        rows_fallback, sql_fallback = direct_sql_pricing_consultation(q)
        if rows_fallback:
            try:
                from tabulate import tabulate
                text_fb = tabulate(rows_fallback, headers="keys" if rows_fallback and isinstance(rows_fallback[0], dict) else [], tablefmt="github")
            except Exception:
                text_fb = str(rows_fallback)
            return {"ok": True, "sql": sql_fallback, "rows": rows_fallback, "text": text_fb}
        return {"ok": False, "sql": sql, "rows": [], "text": ""}

def run_docs(q: str):
    try:
        docs = retriever.invoke(expand_query_for_clinic(q)) or []
        snippets = []
        for d in docs:
            content = getattr(d, "page_content", "")
            if content:
                snippets.append(content.strip())
        text = "\n\n---\n\n".join(snippets)
        return {"ok": bool(text.strip()), "text": text, "docs": docs}
    except Exception:
        return {"ok": False, "text": "", "docs": []}


def build_context_from_results(results: dict) -> str:
    parts = []
    if results.get("sql", {}).get("ok") and results["sql"].get("text"):
        parts.append("## Structured Results (SQL)\\n" + results["sql"]["text"])
    if results.get("docs", {}).get("ok") and results["docs"].get("text"):
        parts.append("## Unstructured Context (Docs)\\n" + results["docs"]["text"])
    return "\\n\\n".join(parts).strip()

def preprocess(question: str):
    lang = detect_language(question)
    sanitized, _ = sanitize_text_for_llm(question, lang)
    intent = intent_chain.invoke({"text": sanitized})
    if getattr(intent, "intent", None) == "internal_ops" and float(getattr(intent, "confidence", 0.0)) >= 0.6:
        refusal = PUBLIC_REFUSAL.get(lang, PUBLIC_REFUSAL["en"])
        return {"final": refusal, "lang": lang, "sanitized": sanitized}
    return {"lang": lang, "sanitized": sanitized}

def answer(question: str, session_id: str = "default") -> str:
    if not api_is_ready():
        raise HTTPException(status_code=401, detail="OpenAI API key not set or invalid. Please set it first.")
    
    pre = preprocess(question)
    if "final" in pre:
        return pre["final"]

    routed = router.invoke({"question": pre["sanitized"]})
    if routed.route == "sql" and routed.confidence >= 0.6:
        results = {"sql": run_sql(question), "docs": {"ok": False, "text": "", "docs": []}}
    elif routed.route == "docs" and routed.confidence >= 0.6:
        results = {"sql": {"ok": False, "text": "", "rows": []}, "docs": run_docs(question)}
    else:
        results = RunnableParallel(sql=RunnableLambda(lambda x: run_sql(x)), docs=RunnableLambda(lambda x: run_docs(x))).invoke(question)

    context = build_context_from_results(results)
    booking_base = get_janeapp_base() or JANEAPP_BASE or ""
    target_lang = "zh-Hant" if pre["lang"].startswith("zh") else "en"
    
    raw = generator_with_history.invoke({
            "query": pre["sanitized"], 
            "context": context,
            "booking_base": booking_base,
            "target_lang": target_lang
        }, 
        config={"configurable": {"session_id": session_id}})
    safe = redact_text_before_return(raw, pre["lang"])
    return raw
