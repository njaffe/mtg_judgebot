"""
FastAPI Application — JudgeBot LLM Proxy

Serves as the entrypoint for the LLM proxy service. Exposes REST endpoints for:
- `/v1/chat/completions`: Unified LLM chat interface (routes to vendor clients)
- `/health`: Health check endpoint

Handles caching, metering, and vendor routing across OpenAI and Anthropic.
"""

from __future__ import annotations

import os
import time
from typing import List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from models import ChatRequest, ChatResponse, Choice, Message, Usage
import cache as cache_mod
import metering
from llm_vendors import call_openai, call_anthropic, cost_usd

app = FastAPI(title="JudgeBot LLM Proxy", version="0.1.0")

DEFAULT_VENDOR = os.getenv("LLM_DEFAULT_VENDOR", "openai")
DEFAULT_MODEL = os.getenv("LLM_DEFAULT_MODEL", "gpt-4o-mini")

# --- Trivial auth stub (replace with JWT or header parsing later)
class User(BaseModel):
    id: str

def get_user() -> User:
    # Parse Authorization in real code
    return User(id="demo-user")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/v1/chat/completions")
async def chat(req: ChatRequest, user: User = Depends(get_user)):
    payload = req.model_dump()

    # Cache check
    if req.use_cache:
        cached = cache_mod.get(payload)
        if cached:
            usage = Usage(
                prompt_tokens=0,
                completion_tokens=max(len(cached) // 4, 1),
                total_tokens=max(len(cached) // 4, 1),
                cost_usd=0.0,
                latency_ms=0,
            )
            return ChatResponse(
                model=req.model or DEFAULT_MODEL,
                vendor=req.vendor or DEFAULT_VENDOR,
                choices=[Choice(index=0, message=Message(role="assistant", content=cached))],
                usage=usage,
                cache_hit=True,
            )

    vendor = (req.vendor or DEFAULT_VENDOR).lower()
    model = req.model or DEFAULT_MODEL

    start = time.time()
    try:
        if vendor == "openai":
            result = await call_openai(model, [m.model_dump() for m in req.messages], req.temperature, req.max_tokens or 512)
        elif vendor == "anthropic":
            result = await call_anthropic(model, [m.model_dump() for m in req.messages], req.temperature, req.max_tokens or 512)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported vendor: {vendor}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    latency_ms = int((time.time() - start) * 1000)

    prompt_tokens = int(result.get("prompt_tokens", 0))
    completion_tokens = int(result.get("completion_tokens", 0))
    total_tokens = prompt_tokens + completion_tokens
    cost = cost_usd(vendor, model, prompt_tokens, completion_tokens)

    # Metering
    metering.record(
        user.id,
        metering.Meter(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            vendor=vendor,
            model=model,
        ),
    )

    text = result["content"]

    # Cache set
    if req.use_cache and text:
        cache_mod.set(payload, text)

    resp = ChatResponse(
        model=model,
        vendor=vendor,
        choices=[Choice(index=0, message=Message(role="assistant", content=text))],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
        ),
        cache_hit=False,
    )
    return JSONResponse(resp.model_dump())