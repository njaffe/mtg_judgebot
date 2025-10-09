"""
Pydantic Models — JudgeBot LLM Proxy

Defines the request and response schemas used by the FastAPI service:
- ChatRequest: user messages, vendor/model info, and settings
- ChatResponse: normalized output including text, usage, and metadata
- Shared models (Message, Choice, Usage) ensure consistent API shape
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    vendor: Optional[str] = None    # "openai" | "anthropic" | "google" (if you add Gemini later)
    temperature: float = 0.2
    max_tokens: Optional[int] = 512
    metadata: Optional[Dict[str, Any]] = None
    use_cache: bool = True

class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str] = None

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float = 0.0
    latency_ms: int = 0

class ChatResponse(BaseModel):
    id: str = Field(default_factory=lambda: "resp_")
    model: str
    vendor: str
    choices: List[Choice]
    usage: Usage
    cache_hit: bool = False