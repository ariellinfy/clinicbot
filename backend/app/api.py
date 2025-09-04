from http.client import HTTPException
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware

from .utils.config import ALLOW_ORIGINS, DATA_DIR
from .utils.db import get_engine, ensure_tables
from .models.types import ChatIn, IngestIn, ResetIn, SetKeyReq
from .services.ingestion import ingest_directory
from .services.pipeline import answer, api_is_ready, clear_session, set_openai_key

app = FastAPI(title="TCM Clinic Chatbot API")

@app.on_event("startup")
def _auto_ingest_on_startup():
    # Don't ingest until API key is set; embedding needs the key.
    engine = get_engine()
    ensure_tables(engine)
    print("[INFO] API started. Waiting for /set-api-key to ingest data.")
        
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
    if not api_is_ready():
        raise HTTPException(status_code=401, detail="OpenAI API key not set or invalid")
    resp = answer(req.message, session_id=req.session_id or "default")
    return {"reply": resp}

@app.post("/ingest")
def ingest(req: IngestIn):
    dir_path = req.dir_path or DATA_DIR
    engine = get_engine()
    ensure_tables(engine)
    count = ingest_directory(engine, dir_path)
    return {"processed_files": count, "dir": dir_path}

@app.post("/reset-session")
def reset_session(req: ResetIn):
    clear_session(req.session_id or "default")
    return {"ok": True}

@app.post("/set-api-key")
def set_api_key(req: SetKeyReq):
    ok = set_openai_key(req.api_key.strip())
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid API key")
    # Now we can ingest (needs embeddings). Safe re-run.
    engine = get_engine()
    ensure_tables(engine)
    try:
        ingest_directory(engine, DATA_DIR)
    except Exception as e:
        # Not fatal for using the app; vector search may be partial.
        print(f"[WARN] Ingest after key set failed: {e}")
    return {"ok": True}