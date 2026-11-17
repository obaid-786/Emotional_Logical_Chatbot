import asyncio
from typing import AsyncIterator
from google import genai
from google.genai import types
from . import config

# Initialize the native Gemini client
client = genai.Client(api_key=config.LLM_API_KEY)

async def chat(messages, temperature=0.7, json_mode=False, retries=2) -> str:
    contents = []
    for msg in messages:
        role = "user" if msg["role"] in ["user", "system"] else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
    
    config_params = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json" if json_mode else "text/plain"
    )

    for attempt in range(retries + 1):
        try:
            response = await client.aio.models.generate_content(
                model=config.LLM_MODEL,
                contents=contents,
                config=config_params
            )
            return response.text or ""
        except Exception as e:
            print(f"[llm.chat] FAILED: {e!r}", flush=True)
            if attempt == retries:
                raise
            await asyncio.sleep(0.5 * (2 ** attempt))

async def chat_stream(messages, temperature=0.7, retries=2) -> AsyncIterator[str]:
    contents = []
    for msg in messages:
        role = "user" if msg["role"] in ["user", "system"] else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

    config_params = types.GenerateContentConfig(temperature=temperature)

    for attempt in range(retries + 1):
        try:
            response_stream = await client.aio.models.generate_content_stream(
                model=config.LLM_MODEL,
                contents=contents,
                config=config_params
            )
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
            return
        except Exception as e:
            print(f"[chat_stream] attempt {attempt+1} failed: {e!r}", flush=True)
            if attempt == retries:
                yield "[I'm having trouble reaching my brain. Please try again.]"
                return
            await asyncio.sleep(0.5 * (2 ** attempt))

async def embed(texts: list[str]) -> list[list[float]]:
    response = await client.aio.models.embed_content(
        model=config.EMBED_MODEL,
        contents=texts,
    )
    return [embedding.values for embedding in response.embeddings]

def estimate_usage(prompt: str, completion: str):
    p = len(prompt) // 4
    c = len(completion) // 4
    return p, c, config.estimate_cost(config.LLM_MODEL, p, c)