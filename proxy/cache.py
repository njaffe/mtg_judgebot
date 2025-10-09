"""
Cache Layer — JudgeBot LLM Proxy

Implements a Redis-backed response cache for chat completions.
Uses a normalized SHA256 key derived from input messages and parameters.
Supports simple get/set operations with configurable TTL.
"""


import hashlib
import json
import os
from typing import Optional
import redis

_redis = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

def _key_for(payload: dict) -> str:
    # Normalize: ignore vendor/model to maximize reuse across same logical request
    norm = {
        "messages": payload.get("messages", []),
        "temperature": payload.get("temperature", 0.2),
        "max_tokens": payload.get("max_tokens", 512),
    }
    digest = hashlib.sha256(json.dumps(norm, sort_keys=True).encode()).hexdigest()
    return f"chatcache:{digest}"

def get(payload: dict) -> Optional[str]:
    val = _redis.get(_key_for(payload))
    return val.decode() if val else None

def set(payload: dict, response_text: str, ttl_seconds: int = 86400):
    _redis.setex(_key_for(payload), ttl_seconds, response_text)