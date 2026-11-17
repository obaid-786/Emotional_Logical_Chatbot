import os, chromadb
from .llm import embed
from . import config

os.makedirs(config.CHROMA_PATH, exist_ok=True)
_db = chromadb.PersistentClient(path=config.CHROMA_PATH)
_col = _db.get_or_create_collection("knowledge_base")

async def ingest(doc_id: str, text: str):
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
    if not chunks: return
    embs = await embed(chunks)
    _col.upsert(ids=[f"{doc_id}-{i}" for i in range(len(chunks))],
                documents=chunks, embeddings=embs)

async def retrieve(query: str, k=3) -> list[str]:
    try:
        e = (await embed([query]))[0]
        res = _col.query(query_embeddings=[e], n_results=k)
        return res["documents"][0] if res["documents"] else []
    except Exception:
        return []