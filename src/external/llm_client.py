"""
Configurable LLM provider client for JudgeBot.

Dispatches chat completions to the configured provider while preserving the
OpenAI-like response shape used by the existing Anthropic client.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from src.external import anthropic_client

load_dotenv(override=True)

DEFAULT_PROVIDER = "anthropic"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


def _provider() -> str:
    return os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower()


def _default_model() -> Optional[str]:
    return os.getenv("LLM_MODEL") or None


def _chat_openai_compatible(
    *,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: Optional[int] = 1500,
    **kwargs: Any,
) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for OpenAI-compatible calls.")

    chosen_model = model or _default_model() or DEFAULT_OPENAI_MODEL
    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL).rstrip("/")
    url = f"{base_url}/chat/completions"

    payload: Dict[str, Any] = {
        "model": chosen_model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    timeout = kwargs.pop("timeout", 120)
    for key, value in kwargs.items():
        if value is not None:
            payload[key] = value

    start_time = time.time()
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"OpenAI-compatible API error: {e}") from e
    except ValueError as e:
        raise RuntimeError("OpenAI-compatible API returned invalid JSON.") from e

    usage = data.get("usage", {}) or {}
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens) or 0

    return {
        "model": data.get("model", chosen_model),
        "vendor": "openai",
        "choices": data.get("choices", []),
        "usage": {
            **usage,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "latency_ms": int((time.time() - start_time) * 1000),
        },
        "cache_hit": False,
    }


def chat(
    *,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: Optional[int] = 1500,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Call the configured LLM provider.

    LLM_PROVIDER defaults to "anthropic" for backward compatibility.
    """
    provider = _provider()
    chosen_model = model or _default_model()

    if provider == "anthropic":
        return anthropic_client.chat(
            messages=messages,
            model=chosen_model,
            temperature=temperature,
            max_tokens=max_tokens or 1500,
            **kwargs,
        )
    if provider == "openai":
        return _chat_openai_compatible(
            messages=messages,
            model=chosen_model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{provider}'. Expected 'anthropic' or 'openai'."
    )
