"""
RAG Service for MTG Judge Bot

This module provides a service class for RAG database operations using FAISS.
Embeddings use the OpenAI SDK (direct). Chat completions go through the LLM adapter
(src.external.openai_client.chat), which can route to the proxy when enabled.
"""

from __future__ import annotations

import os
import pickle
import faiss
import numpy as np
from typing import Optional, List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Adapter for chat (proxy-aware)
from src.external import openai_client

# Load environment variables
load_dotenv()
# After load_dotenv()
USE_PROXY = os.getenv("USE_LLM_PROXY", "false").lower() == "true"
PROXY_BASE = os.getenv("PROXY_BASE_URL", "")
if USE_PROXY:
    print(f"[LLM ROUTING] Using PROXY at {PROXY_BASE or 'http://localhost:8080'}")
else:
    print("[LLM ROUTING] Calling OpenAI directly (V1 mode)")



class RAGService:
    """Service class for RAG database operations using FAISS."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        faiss_index_path: Optional[str] = None,
        embedding_model: Optional[str] = None,
        default_chat_model: Optional[str] = None,
        default_chat_vendor: Optional[str] = None,
    ):
        """
        Initialize the RAG service.

        Args:
            openai_api_key: OpenAI API key (for embeddings)
            faiss_index_path: Path to FAISS index
            embedding_model: Embedding model name
            default_chat_model: Preferred chat model (if None, defaults from env/proxy)
            default_chat_vendor: "openai" | "anthropic" | None (proxy default if None)
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.faiss_index_path = faiss_index_path or os.getenv("FAISS_INDEX_PATH")
        self.embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
        self.default_chat_model = default_chat_model or os.getenv("LLM_DEFAULT_MODEL", None)
        self.default_chat_vendor = default_chat_vendor or os.getenv("LLM_DEFAULT_VENDOR", None)

        if not all([self.openai_api_key, self.faiss_index_path]):
            raise ValueError("OpenAI API key and FAISS index path are required")

        self.client = OpenAI(api_key=self.openai_api_key)

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

    def _embed_query(self, query: str) -> np.ndarray:
        """Embed the query using OpenAI's embedding model (direct SDK)."""
        response = self.client.embeddings.create(input=query, model=self.embedding_model)
        embedding = np.array(response.data[0].embedding, dtype=np.float32)
        return embedding

    def _search_similar_documents(self, query_embedding: np.ndarray, index, documents, top_k=3):
        """Search for the most similar documents."""
        D, I = index.search(np.expand_dims(query_embedding, axis=0), top_k)
        matched_docs = [documents[idx] for idx in I[0]]
        return matched_docs

    def _create_prompt(self, context_documents, query_text):
        """Create a prompt for the LLM using context documents and the query."""
        context_text = "\n\n---\n\n".join(doc["content"] for doc in context_documents)
        prompt = (
            "You are an expert Magic: The Gathering rules assistant. "
            "Based on the following context from the official MTG rules:\n\n"
            f"{context_text}\n\n"
            f"Answer the user's question:\n\n"
            f"{query_text}\n\n"
            "Provide a clear, accurate answer based on the rules context. "
            "If the context doesn't contain enough information, say so."
        )
        return prompt

    def _chat_completion(self, prompt: str, temperature: float = 0.0) -> str:
        """
        Send the prompt to the chat model via the adapter (proxy-aware).
        Falls back to direct if USE_LLM_PROXY is false.
        """
        messages = [
            {"role": "system", "content": "You are a helpful Magic: The Gathering rules assistant."},
            {"role": "user", "content": prompt},
        ]
        resp = openai_client.chat(
            messages=messages,
            model=self.default_chat_model,
            vendor=self.default_chat_vendor,
            temperature=temperature,
            max_tokens=1000,
            use_cache=True,
        )
        return resp["choices"][0]["message"]["content"]

    def query(self, query_text: str) -> str:
        """
        Query the RAG database.

        Returns:
            RAG database response (a synthesized answer grounded in retrieved context).
        """
        try:
            # Load FAISS index and documents
            index, documents = self._load_faiss_index_and_documents()

            # Embed the query
            query_embedding = self._embed_query(query_text)

            # Search for similar documents
            matched_docs = self._search_similar_documents(query_embedding, index, documents, top_k=3)

            # Create a prompt for the LLM
            prompt = self._create_prompt(matched_docs, query_text)

            # Chat via adapter (proxy-aware)
            response_text = self._chat_completion(prompt)

            return response_text

        except Exception as e:
            return f"Error querying RAG database: {str(e)}"