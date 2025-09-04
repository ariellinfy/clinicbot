
import os
from urllib.parse import urlparse
from sqlalchemy import create_engine, text as sql_text
from sqlalchemy.engine import Engine
from .config import SQLITE_URL, JANEAPP_BASE
from ..models.schema import metadata

def get_engine() -> Engine:
    # ensure parent dir exists
    if SQLITE_URL.startswith("sqlite:////"):
        path = SQLITE_URL.replace("sqlite:////", "")
        os.makedirs(os.path.dirname(path), exist_ok=True)
    return create_engine(SQLITE_URL, future=True)

def ensure_tables(engine: Engine):
    metadata.create_all(engine)

def fetch_rows(sql: str, params: dict | None = None):
    """Run a SELECT and return a list[dict] for easy downstream use."""
    try:
        eng = get_engine()
        with eng.connect() as conn:
            result = conn.execute(sql_text(sql), params or {})
            return [dict(r._mapping) for r in result]
    except Exception:
        return []

def get_janeapp_base() -> str | None:
    try:
        rows = fetch_rows(
            "SELECT booking_link FROM clinic_info WHERE booking_link IS NOT NULL ORDER BY updatedAt DESC LIMIT 1;"
        )
        link = rows[0]["booking_link"] if rows else None
        if link:
            u = urlparse(link)
            if u.scheme and u.netloc:
                return f"{u.scheme}://{u.netloc}"
    except Exception:
        pass
    return JANEAPP_BASE or None

def expand_query_for_clinic(q: str) -> str:
    """
    Add synonyms for common intents (pricing, consultation) in EN/ZH to improve recall.
    """
    if not q:
        return q
    q_lower = q.lower()
    expansions = []
    # Pricing synonyms
    if any(x in q_lower for x in ["price", "cost", "fee", "how much", "charge", "consult", "initial"]):
        expansions += ["price", "prices", "cost", "fee", "fees", "charge", "charges"]
    # Consultation synonyms (EN)
    if any(x in q_lower for x in ["consult", "initial", "first visit", "assessment"]):
        expansions += ["consultation", "initial consultation", "first visit", "assessment"]
    # Chinese hints
    zh_terms = ["費用", "價錢", "收費", "多少錢", "幾錢", "諮詢", "初診", "首次就診", "評估"]
    if any(x in q for x in zh_terms):
        expansions += ["費用", "價錢", "收費", "諮詢", "初診", "首次就診", "評估"]
    # Compose expanded query (simple OR-ish text for retriever/LLM)
    expansions = list(dict.fromkeys([e for e in expansions if e]))  # de-dup
    if not expansions:
        return q
    return q + " | " + " | ".join(expansions)

def direct_sql_pricing_consultation(raw_q: str):
    patterns = ["consult", "initial", "assessment", "first", "諮詢", "初診", "首次", "評估"]
    like = " OR ".join(
        [f"LOWER(item) LIKE '%{p}%'" for p in patterns]
        + [f"LOWER(type) LIKE '%{p}%'" for p in patterns]
        + [f"LOWER(category) LIKE '%{p}%'" for p in patterns]
    )
    sql = (
        "SELECT item, type, category, price, max "
        "FROM pricing "
        f"WHERE {like} "
        "ORDER BY price IS NULL, price ASC LIMIT 10;"
    )
    rows = fetch_rows(sql)
    return rows, sql