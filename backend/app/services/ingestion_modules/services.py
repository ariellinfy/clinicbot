from datetime import datetime
from typing import Any, Dict

from .utils import chroma_upsert, delete_children, to_list, upsert
from ...models.schema import (services, service_specialties)

def ingest_services(conn, payload: Dict[str, Any]):
    items = payload["data"] if "data" in payload else to_list(payload)
    docs = []
    for s in items:
        row = {
            "id": s["id"],
            "name": s.get("name"),
            "subtitle": s.get("subtitle"),
            "subtitle_zh": s.get("subtitle_zh"),
            "updatedAt": s.get("updatedAt") or datetime.utcnow().isoformat(),
        }
        upsert(conn, services, row, pk="id")
        delete_children(conn, service_specialties, "service_id", s["id"])
        for spec in to_list(s.get("relatedSpecialties")):
            conn.execute(service_specialties.insert().values(service_id=s["id"], specialty=spec))
        text = "\\n".join([
            f"Service: {s.get('name')} ({s['id']})",
            f"Subtitle: {s.get('subtitle')}",
            f"副標題 (ZH): {s.get('subtitle_zh')}",
            f"Short: {s.get('shortDescription')}",
            f"簡述 (ZH): {s.get('shortDescription_zh')}",
            f"Long: {s.get('longDescription')}",
            f"詳細 (ZH): {s.get('longDescription_zh')}",
            f"Specialties: {', '.join(to_list(s.get('relatedSpecialties')))}",
            f"Updated: {row['updatedAt']}",
        ])
        docs.append((f"service::{s['id']}", text, {"type":"service","id":s["id"],"name":s.get("name")}))
    chroma_upsert(docs)