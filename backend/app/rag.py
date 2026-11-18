import os
import json
import asyncio
from typing import List

import faiss
import numpy as np
from FlagEmbedding import BGEM3FlagModel   # ← BGE-M3-specific class

from . import config

os.makedirs(config.DATA_PATH, exist_ok=True)
os.makedirs(os.path.dirname(config.FAISS_INDEX_PATH) or ".", exist_ok=True)

# BGE-M3 dense embedding dimension
EMBEDDING_DIM = 1024

_model = None
_index = None
_docs: List[str] = []
_lock = asyncio.Lock()  # serialize writes (single-process safe)


def _get_model() -> BGEM3FlagModel:
    """Load BGE-M3 once at first use, then reuse for the process lifetime."""
    global _model
    if _model is None:
        print(f"[RAG] Loading {config.EMBED_MODEL} (device={config.EMBED_DEVICE})...", flush=True)
        _model = BGEM3FlagModel(
            config.EMBED_MODEL,
            use_fp16=(config.EMBED_DEVICE == "cuda"),
            device=config.EMBED_DEVICE,
        )
        print("[RAG] BGE-M3 loaded.", flush=True)
    return _model


def _encode(texts: List[str]) -> np.ndarray:
    """Return L2-normalized float32 dense vectors shaped (N, 1024)."""
    model = _get_model()
    out = model.encode(
        texts,
        batch_size=8,
        max_length=512,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )
    vecs = np.array(out["dense_vecs"], dtype="float32")
    # L2-normalize so IndexFlatIP behaves as cosine similarity
    faiss.normalize_L2(vecs)
    return vecs


def _load_if_exists():
    """Load FAISS index + docs from disk if present. Called once on first query."""
    global _index, _docs
    if _index is not None:
        return
    if os.path.exists(config.FAISS_INDEX_PATH) and os.path.exists(config.FAISS_DOCUMENTS_PATH):
        _index = faiss.read_index(config.FAISS_INDEX_PATH)
        with open(config.FAISS_DOCUMENTS_PATH, "r", encoding="utf-8") as f:
            _docs = json.load(f)
        print(f"[RAG] Loaded FAISS index with {len(_docs)} docs from disk.", flush=True)
    else:
        _index = faiss.IndexFlatIP(EMBEDDING_DIM)
        _docs = []
        print("[RAG] No persisted index — starting fresh.", flush=True)


def _persist():
    """Write index + docs to disk atomically (best-effort)."""
    faiss.write_index(_index, config.FAISS_INDEX_PATH)
    tmp = config.FAISS_DOCUMENTS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_docs, f, ensure_ascii=False)
    os.replace(tmp, config.FAISS_DOCUMENTS_PATH)


async def ingest(doc_id: str, text: str):
    """Split text into paragraph chunks, embed each, add to index, persist."""
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
    if not chunks:
        return

    async with _lock:
        _load_if_exists()

        # De-dupe by doc_id prefix (so re-seeding doesn't duplicate)
        global _docs
        keep_mask = [not d.get("doc_id") == doc_id for d in _docs] if _docs and isinstance(_docs[0], dict) else [True] * len(_docs)

        # If docs are stored as dicts, filter; if plain strings (legacy), rebuild
        if _docs and isinstance(_docs[0], dict):
            new_index = faiss.IndexFlatIP(EMBEDDING_DIM)
            kept = [d for d, keep in zip(_docs, keep_mask) if keep]
            if kept:
                kept_vecs = np.array([d["vec"] for d in kept], dtype="float32")
                new_index.add(kept_vecs)
            global _index
            _index = new_index
            _docs = kept

        vecs = await asyncio.to_thread(_encode, chunks)
        _index.add(vecs)
        for chunk, vec in zip(chunks, vecs):
            _docs.append({"doc_id": doc_id, "text": chunk, "vec": vec.tolist()})

        await asyncio.to_thread(_persist)
        print(f"[RAG] Ingested {len(chunks)} chunks from '{doc_id}'. Total: {len(_docs)}.", flush=True)


async def retrieve(query: str, k: int = 3) -> List[str]:
    """Return up to k most similar document chunks."""
    _load_if_exists()
    if _index is None or _index.ntotal == 0:
        return []
    try:
        qvec = await asyncio.to_thread(_encode, [query])
        k_eff = min(k, _index.ntotal)
        scores, idxs = _index.search(qvec, k_eff)
        results = []
        for i in idxs[0]:
            if i == -1:
                continue
            d = _docs[i]
            results.append(d["text"] if isinstance(d, dict) else d)
        return results
    except Exception as e:
        print(f"[RAG] retrieve failed: {e!r}", flush=True)
        return []