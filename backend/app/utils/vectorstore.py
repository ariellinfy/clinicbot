# backend/app/utils/vectorstore.py
import os
from typing import Optional
import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from .config import OPENAI_EMBED_MODEL

_emb: Optional[OpenAIEmbeddings] = None
_store: Optional[Chroma] = None

def _assert_key():
    if _emb is None:
        raise RuntimeError("OpenAI API key not set. Call /set-api-key first.")


def set_embedding_api_key(new_key: str, model: str | None = None) -> bool:
    """
    Hot-swap the API key (and optionally model) used for **query embeddings**.
    This does NOT re-embed documents; it only affects future queries.
    """
    global _emb, _store
    if not new_key:
        return False
    chosen = model or OPENAI_EMBED_MODEL
    _emb = OpenAIEmbeddings(api_key=new_key, model=chosen)
    # Re-open collection with the new embedding function
    _store = _build_store()
    return True

def get_embeddings() -> OpenAIEmbeddings:
    _assert_key()
    return _emb

def _build_store() -> Chroma:
     # os.makedirs(CHROMA_DIR, exist_ok=True)
     
    # Connect to the remote Chroma client
    # chroma_client = chromadb.HttpClient(host="http://your-chroma-server-ip:8000") # Replace with your server's IP/hostname and port
    chroma_client = chromadb.HttpClient(host=os.getenv("CHROMA_HOST"), port=8000)

    return Chroma(
        collection_name="clinic_data",
        embedding_function=get_embeddings(),
        # persist_directory=CHROMA_DIR,
        client=chroma_client
    )

def get_store() -> Chroma:
    _assert_key()
    global _store
    if _store is None:
        _store = _build_store()
    return _store

def get_retriever(k: int = 4):
    return get_store().as_retriever(search_type="similarity", search_kwargs={"k": k})
