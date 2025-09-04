# backend/app/services/pipeline_modules/query_handlers.py
from ...utils.db import direct_sql_pricing_consultation, expand_query_for_clinic
from . import setup
from ...utils.logging import get_logger

logger = get_logger(__name__)
def run_sql(q: str):
    expanded = expand_query_for_clinic(q)
    sql = setup.sql_chain.invoke({"question": expanded})
    if not sql or not sql.strip():
        return {"ok": False, "sql": "", "rows": [], "text": ""}
    try:
        raw = setup.execute_sql.invoke(sql)
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
        docs = setup.retriever.invoke(expand_query_for_clinic(q)) or []
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
