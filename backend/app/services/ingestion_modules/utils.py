
from typing import Any, Dict, Tuple, List
from sqlalchemy import Table
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ...utils.vectorstore import get_store

# ---------- Utilities ----------
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