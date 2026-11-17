import os

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
LLM_MODEL      = os.getenv("LLM_MODEL", "gemini-3.8-flash")
LLM_API_KEY  = os.getenv("LLM_API_KEY", "")

EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", LLM_BASE_URL)
EMBED_MODEL    = os.getenv("EMBED_MODEL", "gemini-embedding-001")
EMBED_API_KEY  = os.getenv("EMBED_API_KEY", LLM_API_KEY)

CHROMA_PATH = os.getenv("CHROMA_PATH", "data/chroma")
DB_PATH     = os.getenv("DB_PATH", "data/interactions.db")
RATE_LIMIT  = os.getenv("RATE_LIMIT", "30/minute")

# Pricing per 1M tokens (input, output). Unknown models → (0, 0) → cost shows as $0
MODEL_PRICES = {
    "gemini-2.5-flash":       (0.30, 2.50),
    "gemini-2.5-pro":         (1.25, 10.00),
    "gemini-2.0-flash":       (0.10, 0.40),
    "gpt-4o-mini":            (0.15, 0.60),
    "gpt-4o":                 (2.50, 10.00),
    "gpt-3.5-turbo":          (0.50, 1.50),
}

def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    inp, out = MODEL_PRICES.get(model, (0.0, 0.0))
    return (prompt_tokens * inp + completion_tokens * out) / 1_000_000