from datetime import datetime
from typing import Any, Dict

from .utils import chroma_upsert, delete_children, to_list, upsert
from ...models.schema import (team_members, team_specialties, team_languages, team_services)

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