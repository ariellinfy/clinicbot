# backend/app/services/ingestion_modules/clinic.py
from datetime import datetime
from typing import Any, Dict

from .utils import _zh_day_name, chroma_upsert, delete_children, iso_now, to_list, to_uuid, upsert
from ...models.schema import (clinic_info, clinic_hours, clinic_languages, clinic_socials)
from ...utils.vectorstore import get_store

def ingest_clinic_info(conn, payload: Dict[str, Any]):
    data = payload["data"] if "data" in payload else payload
    addr = data.get("address") or {}
    row = {
        "id": to_uuid(data["id"], "clinic"),
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
        "updatedAt": data.get("updatedAt") or iso_now(),
    }
    upsert(conn, clinic_info, row, pk="id")

    clinic_uuid = row["id"]
    delete_children(conn, clinic_hours, "clinic_id", clinic_uuid)
    for h in to_list(data.get("hours")):
        conn.execute(clinic_hours.insert().values(clinic_id=clinic_uuid, day=h.get("day"), open_time=h.get("open"), close_time=h.get("close")))
    delete_children(conn, clinic_languages, "clinic_id", clinic_uuid)
    for lang in to_list(data.get("languages")):
        conn.execute(clinic_languages.insert().values(clinic_id=clinic_uuid, language=lang))

    social = data.get("social_media") or {}
    delete_children(conn, clinic_socials, "clinic_id", clinic_uuid)
    for platform, url in social.items():
        if url: conn.execute(clinic_socials.insert().values(clinic_id=clinic_uuid, platform=platform, url=url))

    # vector docs (EN/ZH cards and hours)
    social_line_en = ""
    social_line_zh = ""
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