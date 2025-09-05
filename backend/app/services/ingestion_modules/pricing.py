# backend/app/services/ingestion_modules/pricing.py
from datetime import datetime
from typing import Any, Dict

from .utils import chroma_upsert, iso_now, to_list, to_uuid, upsert
from ...models.schema import (pricing)

def ingest_pricing(conn, payload: Dict[str, Any]):
    items = payload["data"] if "data" in payload else to_list(payload)
    docs = []
    for p in items:
        service_id = p.get("serviceId") or p.get("service_id")
        row = {
            "id": to_uuid(p["id"], "pricing"),
            "category": p.get("category"),
            "type": p.get("type"),
            "item": p.get("item"),
            "price": p.get("price"),
            "max": p.get("max"),
            "service_id": to_uuid(service_id, "service"),
            "updatedAt": p.get("updatedAt") or iso_now(),
        }
        upsert(conn, pricing, row, pk="id")

        text = "\\n".join([
            f"Pricing Item: {row['item']} ({p['id']})",
            f"Category: {row['category']}",
            f"Type: {row['type']}",
            f"Price: {row['price']}" + (f" (max {row['max']})" if row['max'] is not None else ""),
            f"Service ID: {service_id}",
            f"Updated: {row['updatedAt']}",
        ])
        docs.append((f"pricing::{p['id']}", text, {"type":"pricing","id":p["id"],"category":row["category"],"service_id":service_id}))
    chroma_upsert(docs)