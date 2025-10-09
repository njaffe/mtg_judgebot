# src/external/openai_client.py
"""
LLM adapter for JudgeBot (V2 – proxy-aware)

All app code (Streamlit, CLI, core services) should call only chat(...).
This module decides at runtime to:
  - POST to the FastAPI proxy (/v1/chat/completions) when USE_LLM_PROXY=true, or
  - Call OpenAI directly otherwise.

Return shape always matches the proxy response:
{
  "model": "...",
  "vendor": "...",
  "choices": [{"index": 0, "message": {"role":"assistant","content":"..."}}],
  "usage": {"prompt_tokens":..., "completion_tokens":..., "total_tokens":..., "cost_usd":..., "latency_ms":...},
  "cache_hit": false
}
"""

from __future__ import annotations

import os
from typing import List, Dict, Any, Optional

import requests
from dotenv import load_dotenv

# Optional: direct OpenAI path for V1 behavior
try:
    from openai import OpenAI  # make sure 'openai' is in requirements.txt
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

load_dotenv()

# Routing flags
USE_PROXY: bool = os.getenv("USE_LLM_PROXY", "false").lower() == "true"
PROXY_BASE: str = os.getenv("PROXY_BASE_URL", "http://localhost:8080")

# Defaults (used when model/vendor not provided)
DEFAULT_MODEL: Optional[str] = os.getenv("LLM_DEFAULT_MODEL")  # e.g., "gpt-4o-mini"
DEFAULT_VENDOR: Optional[str] = os.getenv("LLM_DEFAULT_VENDOR")  # e.g., "openai"

# Simple price table for cost estimation in direct mode (USD per 1M tokens).
# Keep in sync with proxy/llm_vendors.py if you update there.
PRICE_TABLE = {
    "openai": {
        "gpt-4o-mini": {"in": 0.15, "out": 0.60},
        "gpt-4o": {"in": 5.00, "out": 15.00},
    },
    # Add others here if you plan to call them directly (Anthropic is via proxy only)
}


def _estimate_cost_usd(vendor: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    v = PRICE_TABLE.get(vendor, {}).get(model)
    if not v:
        return 0.0
    return (prompt_tokens / 1_000_000.0) * v["in"] + (completion_tokens / 1_000_000.0) * v["out"]


def _call_via_proxy(
    *,
    messages: List[Dict[str, str]],
    vendor: Optional[str],
    model: Optional[str],
    temperature: float,
    max_tokens: int,
    use_cache: bool,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "messages": messages,
        "vendor": vendor,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "use_cache": use_cache,
        "metadata": metadata or {},
    }
    resp = requests.post(f"{PROXY_BASE}/v1/chat/completions", json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _call_openai_direct(
    *,
    messages: List[Dict[str, str]],
    model: Optional[str],
    temperature: float,
    max_tokens: int,
) -> Dict[str, Any]:
    """
    Direct call to OpenAI (V1 behavior). Returns proxy-shaped dict.
    """
    if OpenAI is None:
        raise RuntimeError("openai package not available; cannot use direct mode.")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for direct OpenAI calls.")

    client = OpenAI(api_key=api_key)
    chosen_model = model or DEFAULT_MODEL or "gpt-4o-mini"

    # Perform the chat completion
    llm_resp = client.chat.completions.create(
        model=chosen_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    text = llm_resp.choices[0].message.content
    usage = getattr(llm_resp, "usage", None)

    prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
    completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
    total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

    vendor = "openai"
    cost_usd = _estimate_cost_usd(vendor, chosen_model, prompt_tokens or 0, completion_tokens or 0)

    # Build a proxy-like response
    return {
        "model": chosen_model,
        "vendor": vendor,
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": text or ""}},
        ],
        "usage": {
            "prompt_tokens": int(prompt_tokens or 0),
            "completion_tokens": int(completion_tokens or 0),
            "total_tokens": int(total_tokens or 0),
            "cost_usd": float(cost_usd),
            "latency_ms": 0,  # not measured in direct mode
        },
        "cache_hit": False,
    }


def chat(
    *,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    vendor: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 600,
    use_cache: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    The only function your code should call.

    Args:
        messages: OpenAI-style messages [{"role":"system"|"user"|"assistant","content":"..."}]
        model: preferred model (None = use DEFAULT_MODEL or proxy default)
        vendor: preferred vendor ("openai"|"anthropic"|None = proxy default; ignored in direct mode)
        temperature: sampling temperature
        max_tokens: max completion tokens
        use_cache: allow proxy to serve from cache (ignored in direct mode)
        metadata: optional metadata dict (forwarded to proxy)

    Returns:
        dict in proxy shape (see module docstring)
    """
    if USE_PROXY:
        return _call_via_proxy(
            messages=messages,
            vendor=vendor or DEFAULT_VENDOR,
            model=model or DEFAULT_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=use_cache,
            metadata=metadata,
        )
    else:
        # Direct OpenAI path (V1 behavior)
        return _call_openai_direct(
            messages=messages,
            model=model or DEFAULT_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
        )