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