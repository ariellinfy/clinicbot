# backend/app/services/ingestion_modules/services.py
from datetime import datetime
from typing import Any, Dict

from .utils import chroma_upsert, delete_children, iso_now, to_list, to_uuid, upsert
from ...models.schema import (services, service_specialties)

def ingest_services(conn, payload: Dict[str, Any]):
    items = payload["data"] if "data" in payload else to_list(payload)
    docs = []
    for s in items:
        row = {
            "id": to_uuid(s["id"], "service"),
            "name": s.get("name"),
            "subtitle": s.get("subtitle"),
            "subtitle_zh": s.get("subtitle_zh"),
            "updatedAt": s.get("updatedAt") or iso_now(),
        }
        upsert(conn, services, row, pk="id")
        
        service_uuid = row["id"]
        delete_children(conn, service_specialties, "service_id", service_uuid)
        for spec in to_list(s.get("relatedSpecialties")):
            conn.execute(service_specialties.insert().values(service_id=service_uuid, specialty=spec))
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