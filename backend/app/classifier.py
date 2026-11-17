import json
import re
from .llm import chat
from .models import MessageAnalysis

SENSITIVE = ["refund","lawsuit","legal","cancel","manager","complaint","attorney","sue"]

SYSTEM = """Analyze the customer message. Return ONLY a JSON object with these keys:
- "emotion": one of ["angry","frustrated","confused","sad","anxious","happy","neutral"]
- "intent": one of ["question","complaint","request_help","chat","sensitive"]
- "confidence": float 0-1 (your certainty)
No prose. No markdown fences. Only JSON."""

VALID_EMOTIONS = {"angry","frustrated","confused","sad","anxious","happy","neutral"}
VALID_INTENTS  = {"question","complaint","request_help","chat","sensitive"}


def _extract_json(raw: str) -> dict:
    """Gemini (and others) sometimes wrap JSON in ```json ... ``` fences.
    Strip them, then find the first {...} block and parse it."""
    if not raw:
        raise ValueError("empty response")
    s = raw.strip()
    # strip leading/trailing markdown fences
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)
    # pull the outermost {...}
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object found in: {raw[:200]!r}")
    return json.loads(s[start:end + 1])


async def classify(text: str) -> MessageAnalysis:
    # Fast path — no LLM needed
    if any(k in text.lower() for k in SENSITIVE):
        return MessageAnalysis(emotion="angry", intent="sensitive", confidence=1.0)

    try:
        raw = await chat(
            [{"role": "system", "content": SYSTEM},
             {"role": "user",   "content": text}],
            temperature=0.0,
            json_mode=True,
        )
        print(f"[classifier] raw={raw!r}", flush=True)     # DEBUG — remove later
        data = _extract_json(raw)

        # Defensive coercion: unknown values → safe defaults, don't crash
        if data.get("emotion") not in VALID_EMOTIONS:
            data["emotion"] = "neutral"
        if data.get("intent") not in VALID_INTENTS:
            data["intent"] = "chat"
        try:
            data["confidence"] = float(data.get("confidence", 0.7))
        except (TypeError, ValueError):
            data["confidence"] = 0.7
        # clamp
        data["confidence"] = max(0.0, min(1.0, data["confidence"]))

        return MessageAnalysis(**data)

    except Exception as e:
        print(f"[classifier] FAILED: {e!r}", flush=True)
        # Neutral fallback, NOT 0.3 — so we don't escalate on parse errors
        return MessageAnalysis(emotion="neutral", intent="chat", confidence=0.5)