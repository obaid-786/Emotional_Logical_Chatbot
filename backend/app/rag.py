import os
import json
import asyncio
from typing import List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer   # ← general ST model, not BGE-specific

from . import config

os.makedirs(config.DATA_PATH, exist_ok=True)
os.makedirs(os.path.dirname(config.FAISS_INDEX_PATH) or ".", exist_ok=True)

_model = None
_index = None
_docs: List[dict] = []
_lock = asyncio.Lock()  # serialize writes (single-process safe)
_embed_dim = None


def _get_model() -> SentenceTransformer:
    """Load the sentence-transformers model once, reuse for process lifetime."""
    global _model
    if _model is None:
        device = getattr(config, "EMBED_DEVICE", "cpu") or "cpu"
        print(f"[RAG] Loading {config.EMBED_MODEL} (device={device})...", flush=True)
        _model = SentenceTransformer(config.EMBED_MODEL, device=device)
        # Preserve the original 512-token window. MiniLM defaults to 256,
        # which is fine for paragraph chunks but truncates longer ones.
        _model.max_seq_length = 512
        print(
            f"[RAG] Model loaded. dim={_model.get_sentence_embedding_dimension()}",
            flush=True,
        )
    return _model


def _get_dim() -> int:
    """Embedding dimension, read from the model once and cached."""
    global _embed_dim
    if _embed_dim is None:
        _embed_dim = _get_model().get_sentence_embedding_dimension()
    return _embed_dim


def _encode(texts: List[str]) -> np.ndarray:
    """Return L2-normalized float32 dense vectors shaped (N, dim)."""
    model = _get_model()
    vecs = model.encode(
        texts,
        batch_size=8,
        convert_to_numpy=True,
        normalize_embeddings=True,      # replaces the manual faiss.normalize_L2
        show_progress_bar=False,
    ).astype("float32")
    return vecs


def _load_if_exists():
    """Load FAISS index + docs from disk if present. Called once on first query."""
    global _index, _docs
    if _index is not None:
        return

    if os.path.exists(config.FAISS_INDEX_PATH) and os.path.exists(config.FAISS_DOCUMENTS_PATH):
        try:
            idx = faiss.read_index(config.FAISS_INDEX_PATH)
            with open(config.FAISS_DOCUMENTS_PATH, "r", encoding="utf-8") as f:
                docs = json.load(f)
            expected_dim = _get_dim()
            # If you previously ran BGE-M3 (1024 dims) and now switched to
            # MiniLM (384 dims), the old index won't work — rebuild from docs.
            if idx.d == expected_dim:
                _index = idx
                _docs = docs
                print(f"[RAG] Loaded FAISS index with {len(_docs)} docs (dim={idx.d}).", flush=True)
                return
            print(
                f"[RAG] Index dim={idx.d} != model dim={expected_dim} — rebuilding.",
                flush=True,
            )
        except Exception as e:
            print(f"[RAG] Failed to load existing index: {e!r} — rebuilding.", flush=True)

    _index = faiss.IndexFlatIP(_get_dim())
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

        # De-dupe by doc_id so re-seeding doesn't duplicate
        global _docs, _index
        if _docs and isinstance(_docs[0], dict):
            kept = [d for d in _docs if d.get("doc_id") != doc_id]
            if len(kept) != len(_docs):
                new_index = faiss.IndexFlatIP(_get_dim())
                if kept:
                    kept_vecs = np.array([d["vec"] for d in kept], dtype="float32")
                    new_index.add(kept_vecs)
                _index = new_index
                _docs = kept

        vecs = await asyncio.to_thread(_encode, chunks)
        _index.add(vecs)
        for chunk, vec in zip(chunks, vecs):
            _docs.append({"doc_id": doc_id, "text": chunk, "vec": vec.tolist()})

        await asyncio.to_thread(_persist)
        print(
            f"[RAG] Ingested {len(chunks)} chunks from '{doc_id}'. Total: {len(_docs)}.",
            flush=True,
        )


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