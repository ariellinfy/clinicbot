from sqlalchemy import MetaData, Table, Column, String, Integer, ForeignKey, Text, TIMESTAMP, text as sa_text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

metadata = MetaData()

clinic_info = Table(
    "clinic_info", metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()")),
    Column("name", String(100)),
    Column("tagline", String(255)),
    Column("tagline_zh", String(255)),
    Column("street", String(100)),
    Column("city", String(50)),
    Column("province", String(50)),
    Column("postalCode", String(20)),
    Column("country", String(50)),
    Column("phone", String(20)),
    Column("email", String(100)),
    Column("booking_link", String(255)),
    Column("updatedAt", TIMESTAMP(timezone=True), server_default=sa_text("CURRENT_TIMESTAMP")),
)

clinic_hours = Table(
    "clinic_hours", metadata,
    Column("clinic_id", PG_UUID(as_uuid=True), ForeignKey("clinic_info.id")),
    Column("day", String(10)),  # e.g., "Monday"
    Column("open_time", String(8)),  # e.g., "09:00:00"
    Column("close_time", String(8)),
)

clinic_languages = Table(
    "clinic_languages", metadata,
    Column("clinic_id", PG_UUID(as_uuid=True), ForeignKey("clinic_info.id")),
    Column("language", String(50)),
)

clinic_socials = Table(
    "clinic_socials", metadata,
    Column("clinic_id", PG_UUID(as_uuid=True), ForeignKey("clinic_info.id")),
    Column("platform", String(50)),  # e.g., "facebook"
    Column("url", String(255)),
)

team_members = Table(
    "team_members", metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()")),
    Column("type", String(50)),
    Column("janeAppId", Integer),
    Column("firstName", String(50)),
    Column("lastName", String(50)),
    Column("fullName", String(100)),
    Column("prefix", String(20)),
    Column("title", String(100)),
    Column("updatedAt", TIMESTAMP(timezone=True), server_default=sa_text("CURRENT_TIMESTAMP")),
)

team_specialties = Table(
    "team_specialties", metadata,
    Column("practitioner_id", PG_UUID(as_uuid=True), ForeignKey("team_members.id")),
    Column("specialty", String(100)),
)

team_languages = Table(
    "team_languages", metadata,
    Column("practitioner_id", PG_UUID(as_uuid=True), ForeignKey("team_members.id")),
    Column("language", String(50)),
)

team_services = Table(
    "team_services", metadata,
    Column("practitioner_id", PG_UUID(as_uuid=True), ForeignKey("team_members.id")),
    Column("service_id", PG_UUID(as_uuid=True), ForeignKey("services.id")),
)

services = Table(
    "services", metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()")),
    Column("name", String(100)),
    Column("subtitle", String(255)),
    Column("subtitle_zh", String(255)),
    Column("updatedAt", TIMESTAMP(timezone=True), server_default=sa_text("CURRENT_TIMESTAMP")),
)

service_specialties = Table(
    "service_specialties", metadata,
    Column("service_id", PG_UUID(as_uuid=True), ForeignKey("services.id")),
    Column("specialty", String(100)),
)

pricing = Table(
    "pricing", metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()")),
    Column("category", String(50)),
    Column("type", String(50)),
    Column("item", String(100)),
    Column("price", Integer),
    Column("max", Integer),
    Column("service_id", PG_UUID(as_uuid=True), ForeignKey("services.id")),
    Column("updatedAt", TIMESTAMP(timezone=True), server_default=sa_text("CURRENT_TIMESTAMP")),
)

faqs = Table(
    "faqs", metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True, server_default=sa_text("gen_random_uuid()")),
    Column("category", String(50)),
    Column("question", String(255)),
    Column("answer", Text),
    Column("answer_zh", Text),
    Column("keywords", String(255)),
    Column("updatedAt", TIMESTAMP(timezone=True), server_default=sa_text("CURRENT_TIMESTAMP")),
)