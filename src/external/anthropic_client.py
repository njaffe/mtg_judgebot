# src/external/anthropic_client.py
"""
Anthropic client for JudgeBot

Direct Anthropic API client using the official SDK.
Returns the same proxy-shaped response dict for consistency with other clients.

Return shape:
{
  "model": "...",
  "vendor": "anthropic",
  "choices": [{"index": 0, "message": {"role":"assistant","content":"..."}}],
  "usage": {"prompt_tokens":..., "completion_tokens":..., "total_tokens":..., "cost_usd":..., "latency_ms":...},
  "cache_hit": false
}
"""

from __future__ import annotations

import os
import time
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

load_dotenv(override=True)

# Anthropic configuration
DEFAULT_MODEL: str = os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-6")

# Price table (USD per 1M tokens)
PRICE_TABLE = {
    "claude-sonnet-4-6": {"in": 3.00, "out": 15.00},
    "claude-sonnet-4-5": {"in": 3.00, "out": 15.00},
    "claude-haiku-4-5": {"in": 1.00, "out": 5.00},
    "claude-opus-4-6": {"in": 5.00, "out": 25.00},
}


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    prices = PRICE_TABLE.get(model)
    if not prices:
        return 0.0
    return (prompt_tokens / 1_000_000) * prices["in"] + (completion_tokens / 1_000_000) * prices["out"]


def chat(
    *,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    vendor: Optional[str] = None,  # Ignored (always Anthropic)
    temperature: float = 0.2,
    max_tokens: int = 1500,
    use_cache: bool = True,  # Ignored (no built-in caching)
    metadata: Optional[Dict[str, Any]] = None,  # Ignored
) -> Dict[str, Any]:
    """
    Call Anthropic API for chat completion.

    Extracts system messages and passes them via the `system` parameter.
    All other messages are passed as the conversation.

    Returns:
        dict in proxy-compatible shape.
    """
    import anthropic

    chosen_model = model or DEFAULT_MODEL
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required for Anthropic calls.")

    client = anthropic.Anthropic(api_key=api_key)

    # Separate system messages from conversation messages
    system_parts = []
    conversation = []
    for msg in messages:
        if msg["role"] == "system":
            system_parts.append(msg["content"])
        else:
            conversation.append({"role": msg["role"], "content": msg["content"]})

    system_text = "\n\n".join(system_parts) if system_parts else None

    start_time = time.time()

    try:
        kwargs: Dict[str, Any] = {
            "model": chosen_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": conversation,
        }
        if system_text:
            kwargs["system"] = system_text

        response = client.messages.create(**kwargs)

        content = "".join(
            block.text for block in response.content if block.type == "text"
        )

        latency_ms = int((time.time() - start_time) * 1000)
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = _estimate_cost_usd(chosen_model, prompt_tokens, completion_tokens)

        return {
            "model": chosen_model,
            "vendor": "anthropic",
            "choices": [
                {"index": 0, "message": {"role": "assistant", "content": content}},
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
            },
            "cache_hit": False,
        }

    except anthropic.APIError as e:
        raise RuntimeError(f"Anthropic API error: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error calling Anthropic: {e}") from e


if __name__ == "__main__":
    print(chat(messages=[{"role": "user", "content": "What is the capital of France?"}]))
