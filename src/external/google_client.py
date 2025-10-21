"""
Google Client Service for MTG Judge Bot

This module provides a service class for Google Search API integration.
Uses Ollama for local summarization instead of OpenAI.
"""

import os
import time
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class GoogleClient:
    """
    Service class for Google Search API integration.
    """
    
    def __init__(self, 
                 google_api_key: Optional[str] = None,
                 google_cse_id: Optional[str] = None,
                 ollama_base_url: Optional[str] = None,
                 ollama_model: Optional[str] = None):
        """
        Initialize the Google client.
        
        Args:
            google_api_key: Google API key
            google_cse_id: Google Custom Search Engine ID
            ollama_base_url: Ollama server URL (default: http://localhost:11434)
            ollama_model: Ollama model for summarization (default: llama3)
        """
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = google_cse_id or os.getenv("GOOGLE_CSE_ID")
        self.ollama_base_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = ollama_model or os.getenv("OLLAMA_DEFAULT_MODEL", "llama3:latest")
        
        if not all([self.google_api_key, self.google_cse_id]):
            raise ValueError("Google API key and CSE ID are required")
    
    def _summarize_with_ollama(self, prompt: str) -> str:
        """
        Use Ollama to summarize content.
        
        Args:
            prompt: The prompt to send to Ollama
            
        Returns:
            Summarized content from Ollama
        """
        import requests
        
        messages = [
            {"role": "system", "content": "You are a helpful research assistant."},
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "num_predict": 800,
            }
        }
        
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/chat",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")
        except Exception as e:
            return f"Error summarizing with Ollama: {str(e)}"
    
    def search(self, query_text: str) -> str:
        """
        Perform a general Google search and return summarized results.
        
        Args:
            query_text: The search query
            
        Returns:
            Summarized search results
        """
        import requests
        
        # Perform Google search
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.google_cse_id,
            "q": query_text,
            "num": 10
        }

        response = requests.get(url, params=params)
        items = response.json().get("items", [])
        if not items:
            return "No results found for the query."

        summaries = ""
        for idx, item in enumerate(items, 1):
            summaries += f"{idx}. {item.get('title')}\n{item.get('snippet')}\n{item.get('link')}\n\n"

        # Summarize via Ollama
        prompt = f"""You are an expert at extracting useful information from search results.
        
Here is a query: {query_text}

And here are the top results from Google:
{summaries}

Please summarize the most relevant and helpful insights in a concise paragraph:
"""

        return self._summarize_with_ollama(prompt)
    
    def search_reddit(self, query_text: str) -> str:
        """
        Search for Reddit posts via Google and return summarized results.
        
        Args:
            query_text: The search query
            
        Returns:
            Summarized Reddit search results
        """
        import requests
        
        # Specialized Google Search for Reddit posts
        enriched_query = f"{query_text} site:reddit.com (mtgrules OR \"magic the gathering\")"
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.google_cse_id,
            "q": enriched_query,
            "num": 10
        }

        response = requests.get(url, params=params)
        items = response.json().get("items", [])
        if not items:
            return "No relevant Reddit results found via Google."

        # Filter for MTG-related content
        mtg_items = [item for item in items if any(
            keyword in item["title"].lower() for keyword in
            ["mtg", "magic", "ramirez", "rules", "pirate", "graveyard", "card"]
        )]

        if not mtg_items:
            return "No relevant Magic-related Reddit discussions found."

        summaries = ""
        for idx, item in enumerate(mtg_items, 1):
            summaries += f"{idx}. {item.get('title')}\n{item.get('snippet')}\n{item.get('link')}\n\n"

        # Summarize via Ollama
        prompt = f"""You are an MTG expert analyzing Google search results from Reddit.
        
Query: {query_text}

Here are Reddit posts pulled from Google:
{summaries}

Summarize any useful rules insight in a concise and clear paragraph:
"""

        return self._summarize_with_ollama(prompt)