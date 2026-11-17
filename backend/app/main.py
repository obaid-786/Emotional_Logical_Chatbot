import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .models import ChatRequest, FeedbackRequest, ResetRequest
from .classifier import classify
from .router import route
from .agents import therapist_agent, logical_agent, escalate_agent
from .rag import ingest
from .guardrails import is_safe, BLOCKED_RESPONSE
from .pii import redact
from .llm import estimate_usage
from . import database as db
from . import config

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Emotion Chatbot API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

db.init()

FAQ = """Refund Policy: Refunds available within 30 days of purchase for unused products.
Shipping: Standard shipping takes 3-5 business days. Express is 1-2 days.
Support Hours: Team available Monday-Friday 9AM-6PM EST.
Cancellation: Subscriptions can be cancelled anytime from account settings."""

@app.on_event("startup")
async def seed_kb():
    marker = Path("data/kb_seeded")
    if not marker.exists():
        try:
            await ingest("faq", FAQ)
            marker.touch()
        except Exception as e:
            print("KB seed skipped:", e)

def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"

@app.post("/api/chat")
@limiter.limit(config.RATE_LIMIT)
async def chat_endpoint(request: Request, req: ChatRequest):
    async def stream():
        # 1. Guardrail
        if not is_safe(req.message):
            yield sse({"type":"meta","emotion":"neutral","intent":"blocked",
                       "confidence":1.0,"strategy":"blocked"})
            yield sse({"type":"token","text":BLOCKED_RESPONSE})
            yield sse({"type":"done","interaction_id":None})
            return

        # 2. Classify
        analysis = await classify(req.message)
        r = route(analysis)

        # 3. Meta event (UI shows tags immediately)
        yield sse({"type":"meta", "emotion":analysis.emotion,
                   "intent":analysis.intent, "confidence":analysis.confidence,
                   "strategy":r})

        # 4. Persist user turn (redacted in logs, raw in raw column)
        db.add_message(req.session_id, "user", redact(req.message))

        # 5. Stream agent response
        if r == "escalate":
            gen = escalate_agent()
        elif r == "therapist":
            gen = therapist_agent(req.session_id, req.message, analysis.emotion)
        else:
            gen = logical_agent(req.session_id, req.message, analysis.emotion)

        chunks = []
        async for token in gen:
            chunks.append(token)
            yield sse({"type":"token","text":token})

        full = "".join(chunks)
        db.add_message(req.session_id, "assistant", full)

        # 6. Persist interaction + emit id for feedback
        p, c, cost = estimate_usage(req.message + str(analysis), full)
        iid = db.log_interaction(
            req.session_id, req.message, redact(req.message),
            analysis.model_dump(), r, full, p, c, cost,
        )
        yield sse({"type":"done","interaction_id":iid})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@app.post("/api/feedback")
def feedback(req: FeedbackRequest):
    db.add_feedback(req.interaction_id, req.rating, req.comment)
    return {"ok": True}

@app.get("/api/history/{session_id}")
def history(session_id: str):
    return {"messages": db.get_history(session_id, limit=100)}

@app.post("/api/reset")
def reset(req: ResetRequest):
    db.clear_session(req.session_id)
    return {"ok": True}

@app.get("/api/analytics")
def analytics_endpoint():
    return db.analytics()

@app.get("/api/health")
def health():
    return {"status": "ok", "model": config.LLM_MODEL}