import asyncio
from typing import AsyncIterator
from openai import AsyncOpenAI
from . import config

# Groq is OpenAI-compatible — same client, different base_url
client = AsyncOpenAI(
    api_key=config.LLM_API_KEY or "missing-api-key",
    base_url=config.LLM_BASE_URL,
)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


async def chat(messages, temperature=0.7, json_mode=False, retries=2) -> str:
    """Non-streaming chat. Used by classifier.py and as fallback for streaming."""
    request = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        request["response_format"] = {"type": "json_object"}

    for attempt in range(retries + 1):
        try:
            response = await client.chat.completions.create(**request)
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"[llm.chat] attempt {attempt+1} failed: {e!r}", flush=True)
            if attempt == retries:
                raise
            await asyncio.sleep(0.5 * (2 ** attempt))
    return ""  # unreachable


async def chat_stream(messages, temperature=0.7, retries=2) -> AsyncIterator[str]:
    """Streaming chat used by agents.py. Falls back to non-streaming on failure."""
    # Try real streaming first
    for attempt in range(retries + 1):
        try:
            stream = await client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
            return
        except Exception as e:
            print(f"[llm.chat_stream] stream attempt {attempt+1} failed: {e!r}", flush=True)
            if attempt < retries:
                await asyncio.sleep(0.5 * (2 ** attempt))

    # Fallback: non-streaming (Groq occasionally drops long SSE connections)
    print("[llm.chat_stream] falling back to non-streaming", flush=True)
    try:
        response = await client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=temperature,
        )
        yield response.choices[0].message.content or ""
    except Exception as e:
        print(f"[llm.chat_stream] fallback failed: {e!r}", flush=True)
        yield "[I'm having trouble reaching the LLM. Please try again.]"


def estimate_usage(prompt: str, completion: str):
    """Approximate token count + cost. Used by main.py to log per-message cost."""
    p = _estimate_tokens(prompt)
    c = _estimate_tokens(completion)
    return p, c, config.estimate_cost(config.LLM_MODEL, p, c)