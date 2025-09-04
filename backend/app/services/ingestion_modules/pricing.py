from datetime import datetime
from typing import Any, Dict

from .utils import chroma_upsert, to_list, upsert
from ...models.schema import (pricing)

def ingest_pricing(conn, payload: Dict[str, Any]):
    items = payload["data"] if "data" in payload else to_list(payload)
    docs = []
    for p in items:
        row = {
            "id": p["id"],
            "category": p.get("category"),
            "type": p.get("type"),
            "item": p.get("item"),
            "price": p.get("price"),
            "max": p.get("max"),
            "service_id": p.get("serviceId") or p.get("service_id"),
            "updatedAt": p.get("updatedAt") or datetime.utcnow().isoformat(),
        }
        upsert(conn, pricing, row, pk="id")
        text = "\\n".join([
            f"Pricing Item: {row['item']} ({row['id']})",
            f"Category: {row['category']}",
            f"Type: {row['type']}",
            f"Price: {row['price']}" + (f" (max {row['max']})" if row['max'] is not None else ""),
            f"Service ID: {row['service_id']}",
            f"Updated: {row['updatedAt']}",
        ])
        docs.append((f"pricing::{p['id']}", text, {"type":"pricing","id":p["id"],"category":row["category"],"service_id":row["service_id"]}))
    chroma_upsert(docs)