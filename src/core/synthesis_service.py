"""
Synthesis Service for MTG Judge Bot

This module handles the synthesis of responses from multiple sources (RAG, card data,
and optionally Google/Reddit) into a single, coherent answer. Uses the configured LLM
client for high-quality rules reasoning.
"""

from __future__ import annotations

import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

from src.external import llm_client


SYSTEM_PROMPT = (
    "You are an expert Magic: The Gathering certified rules judge providing a final ruling.\n\n"
    "Instructions:\n"
    "- The Comprehensive Rules analysis and card Oracle text are your PRIMARY authority. "
    "Trust these over any other sources.\n"
    "- If supplementary web/community sources are provided, use them only to add context "
    "or detail. Never let them contradict the official rules.\n"
    "- Reason step-by-step for complex interactions involving layers, timestamps, "
    "replacement effects, continuous effects, or priority.\n"
    "- ONLY cite rule numbers that appeared in the rules analysis. Never invent or guess "
    "rule numbers.\n"
    "- Be precise and concise. State the ruling clearly, then explain the reasoning."
)


class SynthesisService:
    """
    Service responsible for synthesizing responses from multiple sources.
    """

    def __init__(
        self,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ):
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _create_synthesis_prompt(
        self,
        rag_response: str,
        query_text: str,
        card_data: str = "",
        google_response: Optional[str] = None,
        reddit_response: Optional[str] = None,
    ) -> str:
        """Create the synthesis prompt for the LLM."""
        parts = [f"=== QUESTION ===\n{query_text}"]

        parts.append(
            "=== PRIMARY AUTHORITY: COMPREHENSIVE RULES ANALYSIS ===\n"
            f"{rag_response}"
        )

        if card_data:
            parts.append(
                "=== CARD ORACLE TEXT & OFFICIAL RULINGS ===\n"
                f"{card_data}"
            )

        if google_response or reddit_response:
            supplementary = "=== SUPPLEMENTARY CONTEXT (use only to add detail, not to contradict the rules) ==="
            if google_response:
                supplementary += f"\n\nWeb Search Results:\n{google_response}"
            if reddit_response:
                supplementary += f"\n\nCommunity Discussion:\n{reddit_response}"
            parts.append(supplementary)

        parts.append(
            "=== TASK ===\n"
            "Provide a clear, authoritative ruling based on the sources above. "
            "If sources conflict, the Comprehensive Rules take precedence."
        )

        return "\n\n".join(parts)

    def synthesize_full_response(
        self,
        rag_response: str,
        query_text: str,
        card_data: str = "",
        google_response: Optional[str] = None,
        reddit_response: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize a full response with all source information.

        Returns:
            Dictionary containing final answer and all source responses.
        """
        prompt = self._create_synthesis_prompt(
            rag_response=rag_response,
            query_text=query_text,
            card_data=card_data,
            google_response=google_response,
            reddit_response=reddit_response,
        )
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": prompt})

        resp = llm_client.chat(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        final_answer = resp["choices"][0]["message"]["content"]
        usage_meta = resp.get("usage", {})

        return {
            "final_answer": final_answer,
            "rag": rag_response,
            "card_data": card_data,
            "google": google_response,
            "reddit": reddit_response,
            "llm_usage": usage_meta,
        }
