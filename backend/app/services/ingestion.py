import os, json
from typing import Any, Iterable, Tuple
from sqlalchemy.engine import Engine

from .ingestion_modules.clinic import ingest_clinic_info
from .ingestion_modules.faqs import ingest_faqs
from .ingestion_modules.pricing import ingest_pricing
from .ingestion_modules.services import ingest_services
from .ingestion_modules.team_members import ingest_team_members
from ..utils.logging import get_logger

logger = get_logger(__name__)

def load_json_files(dir_path: str) -> Iterable[Tuple[str, Any]]:
    if not os.path.isdir(dir_path):
        return []
    for fname in os.listdir(dir_path):
        if fname.lower().endswith(".json"):
            path = os.path.join(dir_path, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    yield fname, json.load(f)
            except Exception as e:
                logger.warning(f"[WARN] Skipping {fname}: {e}")

HANDLERS = {
    "clinic_info": ingest_clinic_info,
    "team_members": ingest_team_members,
    "services": ingest_services,
    "pricing": ingest_pricing,
    "faqs": ingest_faqs,
}

def infer_schema_from_payload(payload: Any) -> str:
    if isinstance(payload, dict) and "schema" in payload:
        return payload["schema"]
    if isinstance(payload, dict) and "id" in payload and "name" in payload and "address" in payload:
        return "clinic_info"
    if isinstance(payload, dict) and "data" in payload:
        data = payload["data"]
        sample = data[0] if isinstance(data, list) and data else data
        if isinstance(sample, dict) and sample.get("title") and ("firstName" in sample or "fullName" in sample):
            return "team_members"
        if isinstance(sample, dict) and "subtitle" in sample and "longDescription" in sample:
            return "services"
        if isinstance(sample, dict) and "category" in sample and "item" in sample and ("serviceId" in sample or "service_id" in sample):
            return "pricing"
        if isinstance(sample, dict) and "question" in sample and "answer" in sample:
            return "faqs"
    raise ValueError("Cannot infer schema from payload; add a 'schema' key.")

def ingest_directory(engine: Engine, dir_path: str) -> int:
    from ..utils.db import ensure_tables
    ensure_tables(engine)
    count = 0
    with engine.begin() as conn:
        for fname, payload in load_json_files(dir_path):
            try:
                schema = infer_schema_from_payload(payload)
                handler = HANDLERS[schema]
                handler(conn, payload)
                count += 1
            except Exception as e:
                logger.error(f"{fname}: {e}", exc_info=True)
    return count
