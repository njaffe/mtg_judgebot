"""
RAG Service for MTG Judge Bot

This module provides a service class for RAG database operations using FAISS.
Embeddings use sentence-transformers (local, no API key needed).
Chat completions use the Anthropic client for higher-quality rules reasoning.
"""

from __future__ import annotations

import os
import pickle
import faiss
import numpy as np
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

from src.external import anthropic_client

# Load environment variables
load_dotenv()

# Default local embedding model — must match what the indexer used
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class RAGService:
    """Service class for RAG database operations using FAISS."""

    def __init__(
        self,
        faiss_index_path: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        self.faiss_index_path = faiss_index_path or os.getenv("FAISS_INDEX_PATH")
        self.embedding_model = embedding_model or os.getenv(
            "EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL
        )

        if not self.faiss_index_path:
            raise ValueError("FAISS index path is required")

        self._encoder = None  # Lazy-loaded

    def _load_faiss_index_and_documents(self):
        """Load FAISS index and documents."""
        index_path = os.path.join(self.faiss_index_path, "faiss.index")
        documents_path = os.path.join(self.faiss_index_path, "documents.pkl")

        if not os.path.exists(index_path) or not os.path.exists(documents_path):
            raise FileNotFoundError(f"FAISS index not found at {self.faiss_index_path}")

        index = faiss.read_index(index_path)
        with open(documents_path, "rb") as f:
            documents = pickle.load(f)
        return index, documents

    def _get_encoder(self):
        """Lazy-load the sentence-transformers model."""
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(self.embedding_model)
        return self._encoder

    def _embed_query(self, query: str) -> np.ndarray:
        """Embed the query using the local sentence-transformers model."""
        encoder = self._get_encoder()
        embedding = encoder.encode(query, convert_to_numpy=True)
        return np.array(embedding, dtype=np.float32)

    def _search_similar_documents(self, query_embedding: np.ndarray, index, documents, top_k=10):
        """Search for the most similar documents."""
        D, I = index.search(np.expand_dims(query_embedding, axis=0), top_k)
        matched_docs = [documents[idx] for idx in I[0] if idx < len(documents)]
        return matched_docs

    def _format_context(self, context_documents: List[Dict[str, Any]]) -> str:
        """Format retrieved documents into context text with rule numbers."""
        parts = []
        for doc in context_documents:
            meta = doc.get("metadata", {})
            doc_type = meta.get("type", "")
            content = doc["content"]

            if doc_type == "rule":
                rule_num = meta.get("rule", "")
                subrules = meta.get("subrules", "")
                header = f"[Rule {rule_num}"
                if subrules:
                    header += f" ({subrules})"
                header += "]"
                parts.append(f"{header}\n{content}")
            elif doc_type == "glossary":
                term = meta.get("term", "")
                parts.append(f"[Glossary: {term}]\n{content}")
            else:
                # Legacy chunks without structured metadata
                parts.append(content)

        return "\n\n---\n\n".join(parts)

    def _create_prompt(self, context_documents: List[Dict[str, Any]], query_text: str, card_data: str = "") -> str:
        """Create a prompt for the LLM using context documents, card data, and the query."""
        context_text = self._format_context(context_documents)

        prompt_parts = []

        if card_data:
            prompt_parts.append(
                "=== CARD ORACLE TEXT & RULINGS ===\n"
                "Use this to understand what the specific cards do:\n\n"
                f"{card_data}"
            )

        prompt_parts.append(
            "=== COMPREHENSIVE RULES CONTEXT ===\n"
            "These are the relevant sections from the official MTG Comprehensive Rules:\n\n"
            f"{context_text}"
        )

        prompt_parts.append(
            f"=== QUESTION ===\n{query_text}"
        )

        return "\n\n".join(prompt_parts)

    def _chat_completion(self, prompt: str, temperature: float = 0.1) -> str:
        """Send the prompt to Claude via the Anthropic client."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert Magic: The Gathering certified rules judge. "
                    "Your role is to provide accurate, authoritative rulings based on "
                    "the Comprehensive Rules.\n\n"
                    "Instructions:\n"
                    "- Reason step-by-step through the interaction, considering layers, "
                    "timestamps, replacement effects, continuous effects, and priority as relevant.\n"
                    "- ONLY cite rule numbers that appear verbatim in the provided Comprehensive Rules context. "
                    "Never invent, guess, or fabricate rule numbers.\n"
                    "- If the provided context does not contain enough information to answer "
                    "confidently, say so explicitly rather than guessing.\n"
                    "- When card-specific Oracle text is provided, use it to understand how the "
                    "cards interact with the rules.\n"
                    "- Be precise and concise. Explain the 'why' behind the ruling."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        resp = anthropic_client.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=1500,
        )
        return resp["choices"][0]["message"]["content"]

    def query(self, query_text: str, card_data: str = "") -> str:
        """
        Query the RAG database.

        Args:
            query_text: The user's question.
            card_data: Formatted card Oracle text and rulings (from Scryfall).

        Returns:
            RAG database response grounded in retrieved context.
        """
        try:
            index, documents = self._load_faiss_index_and_documents()
            query_embedding = self._embed_query(query_text)
            matched_docs = self._search_similar_documents(query_embedding, index, documents, top_k=10)
            prompt = self._create_prompt(matched_docs, query_text, card_data=card_data)
            response_text = self._chat_completion(prompt)
            return response_text
        except Exception as e:
            return f"Error querying RAG database: {str(e)}"
