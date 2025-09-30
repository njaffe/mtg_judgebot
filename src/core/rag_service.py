"""
RAG Service for MTG Judge Bot

This module provides a service class for RAG database operations using FAISS.
"""

import os
import sys
import pickle
import faiss
import numpy as np
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class RAGService:
    """
    Service class for RAG database operations using FAISS.
    """
    
    def __init__(self, 
                 openai_api_key: Optional[str] = None,
                 faiss_index_path: Optional[str] = None):
        """
        Initialize the RAG service.
        
        Args:
            openai_api_key: OpenAI API key
            faiss_index_path: Path to FAISS index
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.faiss_index_path = faiss_index_path or os.getenv("FAISS_INDEX_PATH")
        
        if not all([self.openai_api_key, self.faiss_index_path]):
            raise ValueError("OpenAI API key and FAISS index path are required")
        
        self.client = OpenAI(api_key=self.openai_api_key)
    
    def _load_faiss_index_and_documents(self):
        """
        Load FAISS index and documents.
        """
        index_path = os.path.join(self.faiss_index_path, "faiss.index")
        documents_path = os.path.join(self.faiss_index_path, "documents.pkl")
        
        if not os.path.exists(index_path) or not os.path.exists(documents_path):
            raise FileNotFoundError(f"FAISS index not found at {self.faiss_index_path}")
        
        index = faiss.read_index(index_path)
        with open(documents_path, 'rb') as f:
            documents = pickle.load(f)
        return index, documents
    
    def _embed_query(self, query: str):
        """
        Embed the query using OpenAI's embedding model.
        """
        response = self.client.embeddings.create(
            input=query, 
            model="text-embedding-ada-002"
        )
        embedding = np.array(response.data[0].embedding, dtype=np.float32)
        return embedding
    
    def _search_similar_documents(self, query_embedding, index, documents, top_k=3):
        """
        Search for the most similar documents.
        """
        D, I = index.search(np.expand_dims(query_embedding, axis=0), top_k)
        matched_docs = [documents[idx] for idx in I[0]]
        return matched_docs
    
    def _create_prompt(self, context_documents, query_text):
        """
        Create a prompt for the LLM using context documents and the query.
        """
        context_text = "\n\n---\n\n".join(doc['content'] for doc in context_documents)
        prompt = (
            f"You are an expert Magic: The Gathering rules assistant. "
            f"Based on the following context from the official MTG rules:\n\n"
            f"{context_text}\n\n"
            f"Answer the user's question:\n\n"
            f"{query_text}\n\n"
            f"Provide a clear, accurate answer based on the rules context. "
            f"If the context doesn't contain enough information, say so."
        )
        return prompt
    
    def _query_openai_chat(self, prompt, temperature=0.0):
        """
        Send the prompt to OpenAI's chat model.
        """
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful Magic: The Gathering rules assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=temperature
        )
        return response.choices[0].message.content
    
    def query(self, query_text: str) -> str:
        """
        Query the RAG database.
        
        Args:
            query_text: The query text
            
        Returns:
            RAG database response
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
            
            # Query OpenAI chat model
            response_text = self._query_openai_chat(prompt)
            
            return response_text
            
        except Exception as e:
            return f"Error querying RAG database: {str(e)}"