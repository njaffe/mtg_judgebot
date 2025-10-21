"""
Vendor Integrations — JudgeBot LLM Proxy

Provides async client wrappers for supported LLM vendors:
- OpenAI (Chat Completions API)
- Anthropic (Messages API)

Includes:
- `estimate_tokens()` fallback estimator using tiktoken
- `cost_usd()` utility for cost computation
- Vendor-specific HTTP client functions (`call_openai`, `call_anthropic`)
"""

import os
from typing import Tuple, Dict, Any
import httpx

# Simple price table (USD per 1M tokens). Adjust as needed.
PRICES = {
    "openai": {
        "gpt-4o-mini": {"in": 0.15, "out": 0.60},
        "gpt-4o": {"in": 5.00, "out": 15.00},
    },
    "anthropic": {
        "claude-3-5-sonnet": {"in": 3.00, "out": 15.00},
    },
    "ollama": {
        "llama3": {"in": 0.0, "out": 0.0},
        "llama3.1:8b-instruct": {"in": 0.0, "out": 0.0},
    },
}

def estimate_tokens(messages) -> Tuple[int, int]:
    """Rough token estimate if vendor doesn't return usage."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        text = "\n".join([m["role"] + ": " + m["content"] for m in messages])
        return len(enc.encode(text)), 0
    except Exception:
        chars = sum(len(m["content"]) for m in messages)
        return max(chars // 4, 1), 0

def cost_usd(vendor: str, model: str, in_tok: int, out_tok: int) -> float:
    v = PRICES.get(vendor, {}).get(model)
    if not v:
        return 0.0
    return (in_tok / 1_000_000) * v["in"] + (out_tok / 1_000_000) * v["out"]



import os
import httpx
from typing import Dict, Any

async def call_ollama(model: str, messages, temperature: float, max_tokens: int) -> Dict[str, Any]:
    """
    Call a local Ollama model using its native /api/chat endpoint.
    Expects OpenAI-style messages: [{"role": "...", "content": "..."}].
    """
    base = os.getenv("OLLAMA_URL", "http://localhost:11434")
    url = base.rstrip("/") + "/api/chat"

    # Ollama ignores max_tokens in some builds; include if you want via 'options'
    payload: Dict[str, Any] = {
        "model": model,                 # e.g., "llama3" or "llama3.1:8b-instruct"
        "messages": messages,           # same role/content structure
        "stream": False,
        "options": {
            "temperature": temperature,
            # "num_predict": max_tokens,   # uncomment if you want to hard-limit tokens
        },
    }

    timeout = httpx.Timeout(60.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    # Typical fields returned by Ollama:
    # - data["message"]["content"] (assistant text)
    # - data.get("prompt_eval_count") (approx prompt tokens)
    # - data.get("eval_count") (approx generated tokens)
    content = (data.get("message") or {}).get("content", "")
    prompt_tokens = int(data.get("prompt_eval_count") or 0)
    completion_tokens = int(data.get("eval_count") or 0)

    # If counts not available, estimate completion tokens from content length
    if completion_tokens == 0 and content:
        completion_tokens = max(len(content) // 4, 1)

    return {
        "content": content,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }

async def call_openai(model: str, messages, temperature: float, max_tokens: int) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        # Extract usage if present; otherwise estimate
        in_tok = data.get("usage", {}).get("prompt_tokens")
        out_tok = data.get("usage", {}).get("completion_tokens")
        if in_tok is None:
            in_tok, _ = estimate_tokens(messages)
        if out_tok is None:
            out_tok = max_tokens // 2
        content = data["choices"][0]["message"]["content"]
        return {"content": content, "prompt_tokens": int(in_tok), "completion_tokens": int(out_tok)}

async def call_anthropic(model: str, messages, temperature: float, max_tokens: int) -> Dict[str, Any]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    # Convert messages to Anthropic format (they accept role: user/assistant)
    conv = [{"role": m["role"], "content": m["content"]} for m in messages]
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": conv,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        # Anthropic content: list of blocks with "text"
        content = "".join([blk.get("text", "") for blk in data.get("content", [])])
        in_tok = data.get("usage", {}).get("input_tokens")
        out_tok = data.get("usage", {}).get("output_tokens")
        if in_tok is None:
            in_tok, _ = estimate_tokens(messages)
        if out_tok is None:
            out_tok = max_tokens // 2
        return {"content": content, "prompt_tokens": int(in_tok or 0), "completion_tokens": int(out_tok or 0)}