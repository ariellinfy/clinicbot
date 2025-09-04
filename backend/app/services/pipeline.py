# backend/app/services/pipeline.py
from fastapi import HTTPException
from langchain_core.runnables import RunnableLambda, RunnableParallel

from .pii import detect_language, sanitize_text_for_llm, redact_text_before_return
from ..utils.config import JANEAPP_BASE
from ..utils.rules import PUBLIC_REFUSAL
from ..utils.db import get_janeapp_base
from .pipeline_modules import setup
from .pipeline_modules.query_handlers import run_sql, run_docs, build_context_from_results
from ..utils.logging import get_logger

logger = get_logger(__name__)

def preprocess(question: str):
    if setup.intent_chain is None:
        raise HTTPException(status_code=503, detail="LLM intents not initialized. Set the OpenAI key first.")

    lang = detect_language(question)
    sanitized, _ = sanitize_text_for_llm(question, lang)
    intent = setup.intent_chain.invoke({"text": sanitized})
    if getattr(intent, "intent", None) == "internal_ops" and float(getattr(intent, "confidence", 0.0)) >= 0.6:
        refusal = PUBLIC_REFUSAL.get(lang, PUBLIC_REFUSAL["en"])
        return {"final": refusal, "lang": lang, "sanitized": sanitized}
    return {"lang": lang, "sanitized": sanitized}

def answer(question: str, session_id: str = "default") -> str:
    if not setup.api_is_ready():
        raise HTTPException(status_code=401, detail="OpenAI API key not set or invalid. Please set it first.")
    
    pre = preprocess(question)
    if "final" in pre:
        return pre["final"]

    routed = setup.router.invoke({"question": pre["sanitized"]})
    if routed.route == "sql" and routed.confidence >= 0.6:
        results = {"sql": run_sql(question), "docs": {"ok": False, "text": "", "docs": []}}
    elif routed.route == "docs" and routed.confidence >= 0.6:
        results = {"sql": {"ok": False, "text": "", "rows": []}, "docs": run_docs(question)}
    else:
        results = RunnableParallel(sql=RunnableLambda(lambda x: run_sql(x)), docs=RunnableLambda(lambda x: run_docs(x))).invoke(question)

    context = build_context_from_results(results)
    booking_base = get_janeapp_base() or JANEAPP_BASE or ""
    target_lang = "zh-Hant" if pre["lang"].startswith("zh") else "en"
    
    raw = setup.generator_with_history.invoke({
            "query": pre["sanitized"], 
            "context": context,
            "booking_base": booking_base,
            "target_lang": target_lang
        }, 
        config={"configurable": {"session_id": session_id}})
    safe = redact_text_before_return(raw, pre["lang"])
    return raw