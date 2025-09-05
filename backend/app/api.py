# backend/app/api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .utils.config import ALLOW_ORIGINS, DATA_DIR
from .utils.db import get_engine, ensure_tables
from .utils.logging import get_logger, setup_logging
from .models.types import ChatIn, IngestIn, ResetIn, SetKeyReq
from .services.ingestion import ingest_directory
from .services.pipeline import answer
from .services.pipeline_modules import setup

# Configure logging
setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="TCM Clinic Chatbot API")

@app.on_event("startup")
def _auto_ingest_on_startup():
    # Don't ingest until API key is set; embedding needs the key.
    engine = get_engine()
    ensure_tables(engine)
    logger.info("API started. Waiting for /set-api-key to ingest data.")
        
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/chat")
def chat(req: ChatIn):
    logger.info(f"Chat request received for session_id: {req.session_id}")
    if not setup.api_is_ready():
        logger.warning("Chat request received but API not ready.")
        raise HTTPException(status_code=401, detail="OpenAI API key not set or invalid")
    resp = answer(req.message, session_id=req.session_id or "default")
    logger.info("Chat response sent.")
    return {"reply": resp}

@app.post("/ingest")
def ingest(req: IngestIn):
    dir_path = req.dir_path or DATA_DIR
    logger.info(f"Ingestion request received for directory: {dir_path}")
    engine = get_engine()
    ensure_tables(engine)
    try:
        count = ingest_directory(engine, dir_path)
        logger.info(f"Ingestion completed. Processed {count} files.")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
    return {"processed_files": count, "dir": dir_path}

@app.post("/reset-session")
def reset_session(req: ResetIn):
    logger.info(f"Reset session request received for session_id: {req.session_id}")
    setup.clear_session(req.session_id or "default")
    logger.info("Session reset completed.")
    return {"ok": True}

@app.post("/set-api-key")
def set_api_key(req: SetKeyReq):
    logger.info("Set API key request received.")
    ok = setup.set_openai_key(req.api_key.strip())
    if not ok:
        logger.warning("Invalid API key provided.")
        raise HTTPException(status_code=400, detail="Invalid API key")
    # Now we can ingest (needs embeddings). Safe re-run.
    engine = get_engine()
    ensure_tables(engine)
    try:
        ingest_directory(engine, DATA_DIR)
        logger.info("Initial ingestion after API key set completed.")
    except Exception as e:
        # Not fatal for using the app; vector search may be partial.
        logger.error(f"Initial ingestion after API key set failed: {e}", exc_info=True)
    return {"ok": True}