# src/external/ollama_client.py
"""
Ollama client for JudgeBot

This module provides a unified interface for calling Ollama models.
It maintains the same API shape as the proxy for consistency.

Return shape matches the proxy response:
{
  "model": "...",
  "vendor": "ollama",
  "choices": [{"index": 0, "message": {"role":"assistant","content":"..."}}],
  "usage": {"prompt_tokens":..., "completion_tokens":..., "total_tokens":..., "cost_usd":0.0, "latency_ms":...},
  "cache_hit": false
}
"""

from __future__ import annotations

import os
import time
from typing import List, Dict, Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

# Ollama configuration
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL: Optional[str] = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3:latest")  # or "mistral:latest", "codellama:latest", etc.


def _estimate_tokens(text: str) -> int:
    """
    Rough token estimation for Ollama models.
    Most Ollama models use similar tokenization, ~4 chars per token is reasonable.
    """
    return max(len(text) // 4, 1)



def chat(
    *,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    vendor: Optional[str] = None,  # Ignored for Ollama
    temperature: float = 0.2,
    max_tokens: int = 600,
    use_cache: bool = True,  # Ignored for Ollama (no built-in caching)
    metadata: Optional[Dict[str, Any]] = None,  # Ignored for Ollama
) -> Dict[str, Any]:
    """
    Call Ollama API for chat completion by converting messages into a single prompt
    and using /api/generate (non-streaming) for a one-shot completion.

    Returns:
        dict in your existing proxy shape.
    """
    chosen_model = model or DEFAULT_MODEL or "llama3:latest"
    start_time = time.time()

    # Convert messages to a single prompt for /api/generate
    prompt_parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            prompt_parts.append(f"System: {content}")
        elif role == "user":
            prompt_parts.append(f"User: {content}")
        elif role == "assistant":
            prompt_parts.append(f"Assistant: {content}")
        else:
            # Unknown roles are included verbatim but tagged for transparency
            prompt_parts.append(f"{role.capitalize() or 'Unknown'}: {content}")

    # Encourage the model to answer as the assistant
    full_prompt = "\n\n".join(prompt_parts).strip() + "\n\nAssistant:"

    generate_payload = {
        "model": chosen_model,
        "prompt": full_prompt,
        "stream": False,  # single JSON response (easier to handle)
        "options": {
            "temperature": temperature,
            # Only include num_predict if max_tokens is truthy
            **({"num_predict": max_tokens} if max_tokens else {}),
        },
    }

    # Use a session and ignore proxy env vars so localhost calls don't get hijacked
    session = requests.Session()
    session.trust_env = False

    try:
        resp = session.post(f"{OLLAMA_BASE_URL}/api/generate", json=generate_payload, timeout=120)
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            # Try to surface the server's error body for quick diagnosis
            body = ""
            try:
                body = resp.text
            except Exception:
                pass
            # Common helpful hint for 404: model not present or wrong tag
            if resp.status_code == 404:
                raise RuntimeError(
                    f"Ollama API returned 404 for model '{chosen_model}'. "
                    f"Is the model installed? Try:  ollama pull {chosen_model}\n"
                    f"Server said: {body}"
                ) from e
            raise RuntimeError(f"Ollama API returned {resp.status_code}: {body}") from e

        result = resp.json()

        # Ollama /api/generate returns the completion in "response"
        content = result.get("response", "")
        # (Some versions also return "done", "total_duration", etc.—kept in result if you need it.)

        # Timing & rough token accounting
        latency_ms = int((time.time() - start_time) * 1000)
        prompt_text = "\n".join([m.get("content", "") for m in messages])
        prompt_tokens = _estimate_tokens(prompt_text)
        completion_tokens = _estimate_tokens(content)
        total_tokens = prompt_tokens + completion_tokens

        # Local inference ==> $0 cost
        cost_usd = 0.0

        # Normalize to your existing return shape
        return {
            "model": chosen_model,
            "vendor": "ollama",
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

    except requests.RequestException as e:
        # Network/connection issues, timeouts, etc.
        raise RuntimeError(f"Ollama API call failed: {e}") from e
    except Exception as e:
        # Anything unexpected—surface it cleanly
        raise RuntimeError(f"Unexpected error calling Ollama: {e}") from e


if __name__ == "__main__":
    print(chat(messages=[{"role": "user", "content": "What is the capital of France?"}]))