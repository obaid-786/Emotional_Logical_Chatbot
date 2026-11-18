import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM: Groq (OpenAI-compatible) ---
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL    = os.getenv("LLM_MODEL",    "openai/gpt-oss-120b")
LLM_API_KEY  = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY", "")

# --- Embeddings: local BGE-M3 (no API) ---
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
EMBED_DEVICE = os.getenv("EMBED_DEVICE", "cpu")  # "cuda" only if GPU passthrough works

# --- Paths (all env-var-overridable, with sensible defaults) ---
DATA_PATH            = os.getenv("DATA_PATH", "data")
FAISS_INDEX_PATH     = os.getenv("FAISS_INDEX_PATH",     os.path.join(DATA_PATH, "faiss.index"))
FAISS_DOCUMENTS_PATH = os.getenv("FAISS_DOCUMENTS_PATH", os.path.join(DATA_PATH, "faiss_documents.json"))
DB_PATH              = os.getenv("DB_PATH",              os.path.join(DATA_PATH, "interactions.db"))

# --- Misc ---
RATE_LIMIT = os.getenv("RATE_LIMIT", "30/minute")

# --- Pricing (per 1M tokens) ---
# Groq's public pricing changes; check https://groq.com/pricing and update.
# Leaving at 0 disables cost tracking in the dashboard (no crash).
MODEL_PRICES = {
    "openai/gpt-oss-120b": (0.0, 0.0),
    "openai/gpt-oss-20b":  (0.0, 0.0),
    "llama-3.3-70b-versatile": (0.59, 0.79),
}

def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    inp, out = MODEL_PRICES.get(model, (0.0, 0.0))
    return (prompt_tokens * inp + completion_tokens * out) / 1_000_000