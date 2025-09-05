# backend/app/utils/config.py
import os

# Core paths
DATA_DIR = os.getenv("DATA_DIR", "/app/data/json")
# CHROMA_DIR = os.getenv("CHROMA_DIR", "/app/data/chroma_db")
# SQLITE_URL = os.getenv("SQLITE_URL", "sqlite:////app/data/clinic.db")
SQL_DB_URL = os.getenv("SQL_DB_URL", "sqlite:////app/data/clinic.db")
CHROMA_URL = os.getenv("CHROMA_URL", "/app/data/chroma_db")

# Models
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-nano-2025-04-14")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
HF_EMBED_MODEL = os.getenv("HF_EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Service
DEBUG = os.getenv("DEBUG", "false").lower() == "true" # Set to 'false' in production
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "*").split(",") # Restrict origins in production

# JaneApp base, e.g. https://demo.janeapp.com
JANEAPP_BASE = os.getenv("JANEAPP_BASE", "")