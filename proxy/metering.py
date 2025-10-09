"""
Metering Layer — JudgeBot LLM Proxy

Tracks per-request token usage, latency, and estimated cost.
Stores metrics in Redis for lightweight analytics and usage monitoring.
Provides helper classes (Meter) and functions for structured recording.
"""

import os
import redis
from dataclasses import dataclass

_redis = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

@dataclass
class Meter:
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: int
    vendor: str
    model: str

    def to_dict(self):
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "vendor": self.vendor,
            "model": self.model,
        }

def record(user_id: str, meter: Meter):
    pipe = _redis.pipeline()
    pipe.hincrbyfloat("cost:total", meter.vendor, meter.cost_usd)
    pipe.incrby(f"tokens:prompt:{user_id}", meter.prompt_tokens)
    pipe.incrby(f"tokens:completion:{user_id}", meter.completion_tokens)
    pipe.rpush("latency", meter.latency_ms)
    pipe.execute()