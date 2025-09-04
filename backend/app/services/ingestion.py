
import os, json
from datetime import datetime
from typing import Any, Dict, Iterable, Tuple, List
from sqlalchemy import Table
from sqlalchemy.engine import Engine
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ..models.schema import (
    clinic_info, clinic_hours, clinic_languages, clinic_socials,
    team_members, team_specialties, team_languages, team_services,
    services, service_specialties, pricing, faqs
)
from ..utils.vectorstore import get_store

# ---------- Utilities ----------
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
                print(f"[WARN] Skipping {fname}: {e}")

def to_list(v):
    if v is None: return []
    return v if isinstance(v, list) else [v]

def upsert(conn, table: Table, record: Dict[str, Any], pk: str = "id"):
    stmt = sqlite_insert(table).values(**record)
    update_cols = {c.name: stmt.excluded[c.name] for c in table.columns if c.name != pk}
    stmt = stmt.on_conflict_do_update(index_elements=[pk], set_=update_cols)
    conn.execute(stmt)

def delete_children(conn, table: Table, key_col: str, key_val: str):
    conn.execute(table.delete().where(getattr(table.c, key_col) == key_val))

def chunk_text(text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150, separators=["\n\n","\n",". "," ",""])
    return splitter.split_text(text or "")

def chroma_upsert(docs: List[Tuple[str, str, Dict[str, Any]]]):
    if not docs: return
    store = get_store()
    ids = [d[0] for d in docs]
    try:
        store.delete(ids=ids)
    except Exception:
        pass
    chunk_ids, texts, metas = [], [], []
    for doc_id, text, meta in docs:
        for i, ch in enumerate(chunk_text(text)):
            chunk_ids.append(f"{doc_id}::chunk{i+1}")
            texts.append(ch)
            md = dict(meta)
            md["source_id"] = doc_id
            md["chunk_index"] = i+1
            metas.append(md)
    store.add_texts(texts=texts, metadatas=metas, ids=chunk_ids)

def _zh_day_name(en_day: str) -> str:
    mapping = {"Monday":"星期一","Tuesday":"星期二","Wednesday":"星期三","Thursday":"星期四","Friday":"星期五","Saturday":"星期六","Sunday":"星期日"}
    return mapping.get(en_day, en_day)

# ---------- Ingest Handlers (adapted from Colab) ----------
def ingest_clinic_info(conn, payload: Dict[str, Any]):
    data = payload["data"] if "data" in payload else payload
    addr = data.get("address") or {}
    row = {
        "id": data["id"],
        "name": data.get("name"),
        "tagline": data.get("tagline"),
        "tagline_zh": data.get("tagline_zh"),
        "street": addr.get("street"),
        "city": addr.get("city"),
        "province": addr.get("province"),
        "postalCode": addr.get("postalCode"),
        "country": addr.get("country"),
        "phone": data.get("phone"),
        "email": data.get("email"),
        "booking_link": data.get("booking_link"),
        "updatedAt": data.get("updatedAt") or datetime.utcnow().isoformat(),
    }
    upsert(conn, clinic_info, row, pk="id")
    delete_children(conn, clinic_hours, "clinic_id", data["id"])
    for h in to_list(data.get("hours")):
        conn.execute(clinic_hours.insert().values(clinic_id=data["id"], day=h.get("day"), open_time=h.get("open"), close_time=h.get("close")))
    delete_children(conn, clinic_languages, "clinic_id", data["id"])
    for lang in to_list(data.get("languages")):
        conn.execute(clinic_languages.insert().values(clinic_id=data["id"], language=lang))

    social = data.get("social_media") or {}
    delete_children(conn, clinic_socials, "clinic_id", data["id"])
    for platform, url in social.items():
        if url: conn.execute(clinic_socials.insert().values(clinic_id=data["id"], platform=platform, url=url))

    # vector docs (EN/ZH cards and hours)
    social_line_en = ""
    if social: 
        social_line_en = "Social: " + " ".join(f"{k.capitalize()} {v}" for k, v in social.items() if v)
        social_line_zh = "社群：" + " ".join(f"{k.capitalize()} {v}" for k, v in social.items() if v)
    hours_lines_en, hours_lines_zh = [], []
    for h in to_list(data.get("hours")):
        day_en = h.get("day",""); day_zh = _zh_day_name(day_en)
        open_t, close_t = str(h.get("open","")), str(h.get("close",""))
        is_closed = open_t.lower()=="closed" or close_t.lower()=="closed"
        if is_closed:
            hours_lines_en.append(f"{day_en}: Closed")
            hours_lines_zh.append(f"{day_zh}：休診")
        else:
            hours_lines_en.append(f"{day_en}: {open_t}-{close_t}")
            hours_lines_zh.append(f"{day_zh}：{open_t}–{close_t}")
    hours_text_en = "Clinic Hours:\\n" + "\\n".join(hours_lines_en)
    hours_text_zh = "門診時間：\\n" + "\\n".join(hours_lines_zh)
    address_en = f"{row['street']}, {row['city']}, {row['province']} {row['postalCode']}, {row['country']}"
    address_zh = f"{row['country']}{row['province']}{row['city']}{row['street']}（郵編 {row['postalCode']}）"
    card_en = "\\n".join([
        f"Clinic: {row.get('name')}",
        f"Tagline: {row.get('tagline')}",
        f"Address: {address_en}",
        f"Phone: {row.get('phone')}",
        f"Email: {row.get('email')}",
        f"Booking: {row.get('booking_link')}",
        hours_text_en,
        social_line_en,
        f"Updated: {row['updatedAt']}",
    ])
    card_zh = "\\n".join([
        f"診所：{row.get('name')}",
        f"標語：{row.get('tagline_zh')}",
        f"地址：{address_zh}",
        f"電話：{row.get('phone')}",
        f"電郵：{row.get('email')}",
        f"預約：{row.get('booking_link')}",
        hours_text_zh,
        social_line_zh,
        f"更新時間：{row['updatedAt']}",
    ])
    base = f"clinic::{data['id']}"
    try:
        get_store().delete(ids=[base])
    except Exception:
        pass
    docs = [
        (f"{base}::hours::en", hours_text_en, {"type":"clinic","field":"hours","lang":"en","id":data["id"]}),
        (f"{base}::hours::zh", hours_text_zh, {"type":"clinic","field":"hours","lang":"zh","id":data["id"]}),
        (f"{base}::card::en", card_en, {"type":"clinic","field":"card","lang":"en","id":data["id"]}),
        (f"{base}::card::zh", card_zh, {"type":"clinic","field":"card","lang":"zh","id":data["id"]}),
        (f"{base}::tagline::en", row.get("tagline") or "", {"type":"clinic","field":"tagline","lang":"en","id":data["id"]}),
        (f"{base}::tagline::zh", row.get("tagline_zh") or "", {"type":"clinic","field":"tagline","lang":"zh","id":data["id"]}),
    ]
    docs = [d for d in docs if d[1].strip()]
    chroma_upsert(docs)

def ingest_team_members(conn, payload: Dict[str, Any]):
    items = payload["data"] if "data" in payload else to_list(payload)
    docs = []
    for p in items:
        row = {
            "id": p["id"],
            "type": p.get("type"),
            "janeAppId": p.get("janeAppId"),
            "firstName": p.get("firstName"),
            "lastName": p.get("lastName"),
            "fullName": p.get("fullName"),
            "prefix": p.get("prefix"),
            "title": p.get("title"),
            "updatedAt": p.get("updatedAt") or datetime.utcnow().isoformat(),
        }
        upsert(conn, team_members, row, pk="id")
        delete_children(conn, team_specialties, "practitioner_id", p["id"])
        for s in to_list(p.get("specialties")):
            conn.execute(team_specialties.insert().values(practitioner_id=p["id"], specialty=s))
        delete_children(conn, team_languages, "practitioner_id", p["id"])
        for l in to_list(p.get("languages")):
            conn.execute(team_languages.insert().values(practitioner_id=p["id"], language=l))
        delete_children(conn, team_services, "practitioner_id", p["id"])
        for svc in to_list(p.get("servicesOffered")):
            conn.execute(team_services.insert().values(practitioner_id=p["id"], service_id=svc))
        text = "\\n".join([
            f"Practitioner: {p.get('fullName') or ((p.get('firstName') or '') + ' ' + (p.get('lastName') or '')).strip()}",
            f"Title: {p.get('title')}",
            f"Prefix: {p.get('prefix')}",
            f"Specialties: {', '.join(to_list(p.get('specialties')))}",
            f"Languages: {', '.join(to_list(p.get('languages')))}",
            f"Services: {', '.join(to_list(p.get('servicesOffered')))}",
            f"Bio: {p.get('bio')}",
            f"簡介 (ZH): {p.get('bio_zh')}",
            f"Summary: {p.get('briefBio')}",
            f"摘要 (ZH): {p.get('briefBio_zh')}",
            f"Updated: {row['updatedAt']}",
        ])
        docs.append((f"practitioner::{p['id']}", text, {"type":"practitioner","id":p["id"],"title":p.get("title")}))
    chroma_upsert(docs)

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

def ingest_faqs(conn, payload: Dict[str, Any]):
    items = payload["data"] if "data" in payload else to_list(payload)
    docs = []
    for q in items:
        row = {
            "id": q["id"],
            "category": q.get("category"),
            "question": q.get("question"),
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
                print(f"[ERROR] {fname}: {e}")
    return count
