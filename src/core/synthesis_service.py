"""
Synthesis Service for MTG Judge Bot (V2 – proxy-aware)

This module handles the synthesis of responses from multiple sources (RAG, Google, Reddit)
into a single, coherent answer. All LLM calls are funneled through the adapter
`src.external.openai_client.chat(...)`, which decides at runtime whether to call
the FastAPI proxy (V2) or OpenAI directly (V1) based on environment flags.
"""

from __future__ import annotations

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables (.env or process env)
load_dotenv()

# Single integration point for LLM calls
from src.external import openai_client


class SynthesisService:
    """
    Service responsible for synthesizing responses from multiple sources.

    Notes:
    - No direct vendor SDK usage here. The adapter handles:
      * proxy vs direct routing (USE_LLM_PROXY)
      * vendor/model selection (defaults in proxy or env)
      * usage metadata (latency/tokens/cost)
    """

    def __init__(
        self,
        default_model: Optional[str] = None,
        default_vendor: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ):
        """
        Initialize the synthesis service.

        Args:
            default_model: Preferred model (e.g., "gpt-4o-mini"); if None, proxy/app defaults apply.
            default_vendor: "openai" | "anthropic" | None (use proxy default if None)
            temperature: Generation temperature
            max_tokens: Max completion tokens
        """
        self.default_model = default_model or os.getenv("LLM_DEFAULT_MODEL", None)
        self.default_vendor = default_vendor or os.getenv("LLM_DEFAULT_VENDOR", None)
        self.temperature = temperature
        self.max_tokens = max_tokens

    def synthesize_response(
        self,
        rag_response: str,
        google_response: str,
        reddit_response: str,
        query_text: str,
    ) -> str:
        """
        Synthesize responses from multiple sources into a single answer.

        Returns:
            Synthesized response string.
        """
        prompt = self._create_synthesis_prompt(
            rag_response, google_response, reddit_response, query_text
        )

        # Build messages for the adapter (proxy-shaped)
        messages = [
            {"role": "system", "content": "You are a helpful Magic: The Gathering rules assistant."},
            {"role": "user", "content": prompt},
        ]

        # Route through the adapter — proxy or direct based on env flags
        resp = openai_client.chat(
            messages=messages,
            model=self.default_model,
            vendor=self.default_vendor,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            use_cache=True,
        )

        return resp["choices"][0]["message"]["content"]

    def _create_synthesis_prompt(
        self,
        rag_response: str,
        google_response: str,
        reddit_response: str,
        query_text: str,
    ) -> str:
        """
        Create the synthesis prompt for the LLM.
        """
        return (
            "You are a Magic: The Gathering rules expert. A user has asked the following question:\n\n"
            f"{query_text}\n\n"
            "You were given information from three sources:\n\n"
            f"---\nRAG Database Response:\n{rag_response}\n\n"
            f"---\nGoogle Search Summary:\n{google_response}\n\n"
            f"---\nReddit Summary:\n{reddit_response}\n\n"
            "---\n\n"
            "Please write a single clear and authoritative answer to the user's question. "
            "Be concise, cite rules when relevant, and explain any ambiguity if needed."
        )

    def synthesize_full_response(
        self,
        rag_response: str,
        google_response: str,
        reddit_response: str,
        query_text: str,
    ) -> Dict[str, Any]:
        """
        Synthesize a full response with all source information.

        Returns:
            Dictionary containing final answer and all source responses, plus optional LLM usage metadata.
        """
        # Reuse the same messages so we can capture usage/cost metadata too
        prompt = self._create_synthesis_prompt(
            rag_response, google_response, reddit_response, query_text
        )
        messages = [
            {"role": "system", "content": "You are a helpful Magic: The Gathering rules assistant."},
            {"role": "user", "content": prompt},
        ]

        resp = openai_client.chat(
            messages=messages,
            model=self.default_model,
            vendor=self.default_vendor,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            use_cache=True,
        )

        final_answer = resp["choices"][0]["message"]["content"]
        usage_meta = resp.get("usage", {})

        return {
            "final_answer": final_answer,
            "rag": rag_response,
            "google": google_response,
            "reddit": reddit_response,
            "llm_usage": usage_meta,  # latency/tokens/cost if proxy or wrapped direct call
        }