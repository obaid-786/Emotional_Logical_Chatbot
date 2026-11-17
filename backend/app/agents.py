import uuid
from typing import AsyncIterator
from .llm import chat_stream
from .rag import retrieve
from .database import get_history

TONE = {
    "angry":      "The user is ANGRY. Start with ONE short empathetic sentence, then help.",
    "frustrated": "The user is frustrated. Acknowledge briefly, then answer clearly.",
    "sad":        "The user is sad. Be gentle and supportive.",
    "anxious":    "The user is anxious. Reassure briefly, then answer.",
    "confused":   "The user is confused. Explain simply, step-by-step.",
    "happy":      "The user is happy. Match their positive tone.",
    "neutral":    "",
}

async def therapist_agent(session_id, text, emotion) -> AsyncIterator[str]:
    sys = f"You are a compassionate therapist. {TONE[emotion]} Validate feelings, ask thoughtful questions."
    msgs = [{"role":"system","content":sys}, *get_history(session_id, 10),
            {"role":"user","content":text}]
    async for chunk in chat_stream(msgs):
        yield chunk

async def logical_agent(session_id, text, emotion) -> AsyncIterator[str]:
    kb = await retrieve(text, k=3)
    ctx = "\n\n".join(kb) if kb else "(no relevant context)"
    sys = (f"You are a factual assistant. {TONE[emotion]}\n"
           f"Answer clearly. Prefer info from CONTEXT when relevant.\n\nCONTEXT:\n{ctx}")
    msgs = [{"role":"system","content":sys}, *get_history(session_id, 10),
            {"role":"user","content":text}]
    async for chunk in chat_stream(msgs):
        yield chunk

async def escalate_agent() -> AsyncIterator[str]:
    ref = uuid.uuid4().hex[:6].upper()
    yield ("I want to make sure you get the right help. Your request has been flagged as "
           f"priority and a specialist will follow up shortly. Reference: #ESC-{ref}")