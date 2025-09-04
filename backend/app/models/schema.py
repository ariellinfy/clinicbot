
from sqlalchemy import MetaData, Table, Column, String, Integer, ForeignKey

metadata = MetaData()

clinic_info = Table(
    "clinic_info", metadata,
    Column("id", String, primary_key=True),
    Column("name", String),
    Column("tagline", String),
    Column("tagline_zh", String),
    Column("street", String),
    Column("city", String),
    Column("province", String),
    Column("postalCode", String),
    Column("country", String),
    Column("phone", String),
    Column("email", String),
    Column("booking_link", String),
    Column("updatedAt", String),
)

clinic_hours = Table(
    "clinic_hours", metadata,
    Column("clinic_id", String, ForeignKey("clinic_info.id")),
    Column("day", String),
    Column("open_time", String),
    Column("close_time", String),
)

clinic_languages = Table(
    "clinic_languages", metadata,
    Column("clinic_id", String, ForeignKey("clinic_info.id")),
    Column("language", String),
)

clinic_socials = Table(
    "clinic_socials", metadata,
    Column("clinic_id", String, ForeignKey("clinic_info.id")),
    Column("platform", String),   # e.g., "facebook", "instagram"
    Column("url", String),
)

team_members = Table(
    "team_members", metadata,
    Column("id", String, primary_key=True),
    Column("type", String),
    Column("janeAppId", Integer),
    Column("firstName", String),
    Column("lastName", String),
    Column("fullName", String),
    Column("prefix", String),
    Column("title", String),
    Column("updatedAt", String),
)

team_specialties = Table(
    "team_specialties", metadata,
    Column("practitioner_id", String, ForeignKey("team_members.id")),
    Column("specialty", String),
)

team_languages = Table(
    "team_languages", metadata,
    Column("practitioner_id", String, ForeignKey("team_members.id")),
    Column("language", String),
)

team_services = Table(
    "team_services", metadata,
    Column("practitioner_id", String, ForeignKey("team_members.id")),
    Column("service_id", String),
)

services = Table(
    "services", metadata,
    Column("id", String, primary_key=True),
    Column("name", String),
    Column("subtitle", String),
    Column("subtitle_zh", String),
    Column("updatedAt", String),
)

service_specialties = Table(
    "service_specialties", metadata,
    Column("service_id", String, ForeignKey("services.id")),
    Column("specialty", String),
)

pricing = Table(
    "pricing", metadata,
    Column("id", String, primary_key=True),
    Column("category", String),
    Column("type", String),
    Column("item", String),
    Column("price", Integer),
    Column("max", Integer),
    Column("service_id", String, ForeignKey("services.id")),
    Column("updatedAt", String),
)

faqs = Table(
    "faqs", metadata,
    Column("id", String, primary_key=True),
    Column("category", String),
    Column("question", String),
    Column("keywords", String),
    Column("updatedAt", String),
)