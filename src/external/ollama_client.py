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
    Call Ollama API for chat completion.

    Args:
        messages: OpenAI-style messages [{"role":"system"|"user"|"assistant","content":"..."}]
        model: Ollama model name (None = use DEFAULT_MODEL)
        vendor: Ignored (always "ollama")
        temperature: sampling temperature
        max_tokens: max completion tokens
        use_cache: Ignored (Ollama doesn't have built-in caching)
        metadata: Ignored

    Returns:
        dict in proxy shape (see module docstring)
    """
    chosen_model = model or DEFAULT_MODEL or "llama3:latest"
    start_time = time.time()
    
    try:
        # Convert messages to a single prompt for Ollama
        # Ollama's /api/generate expects a single prompt string
        prompt_parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        # Join all parts into a single prompt
        full_prompt = "\n\n".join(prompt_parts) + "\n\nAssistant:"
        
        # Use /api/generate endpoint with the combined prompt
        generate_payload = {
            "model": chosen_model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=generate_payload,
            timeout=120  # Ollama can be slower than cloud APIs
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Extract response content
        content = result.get("response", "")
        
        # Calculate timing
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Estimate token usage (Ollama doesn't always return usage stats)
        prompt_text = "\n".join([msg["content"] for msg in messages])
        prompt_tokens = _estimate_tokens(prompt_text)
        completion_tokens = _estimate_tokens(content)
        total_tokens = prompt_tokens + completion_tokens
        
        # Ollama is free to run locally, so cost is 0
        cost_usd = 0.0
        
        # Build proxy-like response
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
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Ollama API call failed: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error calling Ollama: {str(e)}")

if __name__ == "__main__":
    print(chat(messages=[{"role": "user", "content": "What is the capital of France?"}]))