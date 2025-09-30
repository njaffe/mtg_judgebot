"""
Google Client Service for MTG Judge Bot

This module provides a service class for Google Search API integration.
"""

import os
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
                 openai_api_key: Optional[str] = None):
        """
        Initialize the Google client.
        
        Args:
            google_api_key: Google API key
            google_cse_id: Google Custom Search Engine ID
            openai_api_key: OpenAI API key for summarization
        """
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = google_cse_id or os.getenv("GOOGLE_CSE_ID")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        if not all([self.google_api_key, self.google_cse_id, self.openai_api_key]):
            raise ValueError("Google API key, CSE ID, and OpenAI API key are required")
    
    def search(self, query_text: str) -> str:
        """
        Perform a general Google search and return summarized results.
        
        Args:
            query_text: The search query
            
        Returns:
            Summarized search results
        """
        import requests
        from openai import OpenAI
        
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

        # Summarize via OpenAI
        prompt = f"""You are an expert at extracting useful information from search results.
        
Here is a query: {query_text}

And here are the top results from Google:
{summaries}

Please summarize the most relevant and helpful insights in a concise paragraph:
"""

        client = OpenAI(api_key=self.openai_api_key)
        result = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful research assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.4
        )

        return result.choices[0].message.content
    
    def search_reddit(self, query_text: str) -> str:
        """
        Search for Reddit posts via Google and return summarized results.
        
        Args:
            query_text: The search query
            
        Returns:
            Summarized Reddit search results
        """
        import requests
        from openai import OpenAI
        
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

        # Summarize via OpenAI
        prompt = f"""You are an MTG expert analyzing Google search results from Reddit.
        
Query: {query_text}

Here are Reddit posts pulled from Google:
{summaries}

Summarize any useful rules insight in a concise and clear paragraph:
"""

        client = OpenAI(api_key=self.openai_api_key)
        result = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful Magic: the Gathering judge assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.4
        )

        return result.choices[0].message.content