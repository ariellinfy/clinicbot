
import os

# Core paths
DATA_DIR = os.getenv("DATA_DIR", "/app/data/json")
CHROMA_DIR = os.getenv("CHROMA_DIR", "/app/data/chroma_db")
SQLITE_URL = os.getenv("SQLITE_URL", "sqlite:////app/data/clinic.db")

# Models / APIs
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-nano-2025-04-14")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Service
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "*").split(",")

# JaneApp base, e.g. https://demo.janeapp.com
JANEAPP_BASE = os.getenv("JANEAPP_BASE", "")