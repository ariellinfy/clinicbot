from datetime import datetime
from typing import Any, Dict

from .utils import chroma_upsert, to_list, upsert
from ...models.schema import (faqs)

def ingest_faqs(conn, payload: Dict[str, Any]):
    items = payload["data"] if "data" in payload else to_list(payload)
    docs = []
    for q in items:
        row = {
            "id": q["id"],
            "category": q.get("category"),
            "question": q.get("question"),
            "answer": q.get("answer"),
            "answer_zh": q.get("answer_zh"),
            "keywords": ", ".join(q.get("keywords", [])) if isinstance(q.get("keywords"), list) else q.get("keywords"),
            "updatedAt": q.get("updatedAt") or datetime.utcnow().isoformat(),
        }
        upsert(conn, faqs, row, pk="id")
        text = "\\n".join([
            f"FAQ: {row['question']}",
            f"Category: {row['category']}",
            f"Keywords: {row['keywords']}",
            f"Answer: {q.get('answer')}",
            f"回答 (ZH): {q.get('answer_zh')}",
            f"Updated: {row['updatedAt']}",
        ])
        docs.append((f"faq::{q['id']}", text, {"type":"faq","id":q["id"],"category":row["category"]}))
    chroma_upsert(docs)