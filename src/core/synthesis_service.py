"""
Synthesis Service for MTG Judge Bot

This module handles the synthesis of responses from multiple sources (RAG, Google, Reddit)
into a single, coherent answer.
"""

import os
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SynthesisService:
    """
    Service responsible for synthesizing responses from multiple sources.
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize the synthesis service.
        
        Args:
            openai_api_key: OpenAI API key. If None, will try to load from environment.
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.openai_api_key)
    
    def synthesize_response(
        self, 
        rag_response: str, 
        google_response: str, 
        reddit_response: str, 
        query_text: str
    ) -> str:
        """
        Synthesize responses from multiple sources into a single answer.
        
        Args:
            rag_response: Response from RAG database
            google_response: Response from Google search
            reddit_response: Response from Reddit search
            query_text: Original user query
            
        Returns:
            Synthesized response string
        """
        prompt = self._create_synthesis_prompt(
            rag_response, google_response, reddit_response, query_text
        )
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful Magic: The Gathering rules assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.3,
        )
        
        return response.choices[0].message.content
    
    def _create_synthesis_prompt(
        self, 
        rag_response: str, 
        google_response: str, 
        reddit_response: str, 
        query_text: str
    ) -> str:
        """
        Create the synthesis prompt for the LLM.
        
        Args:
            rag_response: Response from RAG database
            google_response: Response from Google search
            reddit_response: Response from Reddit search
            query_text: Original user query
            
        Returns:
            Formatted prompt string
        """
        return (
            f"You are a Magic: The Gathering rules expert. A user has asked the following question:\n\n"
            f"{query_text}\n\n"
            f"You were given information from three sources:\n\n"
            f"---\nRAG Database Response:\n{rag_response}\n\n"
            f"---\nGoogle Search Summary:\n{google_response}\n\n"
            f"---\nReddit Summary:\n{reddit_response}\n\n"
            f"---\n\n"
            f"Please write a single clear and authoritative answer to the user's question. "
            f"Be concise, cite rules when relevant, and explain any ambiguity if needed."
        )
    
    def synthesize_full_response(
        self, 
        rag_response: str, 
        google_response: str, 
        reddit_response: str, 
        query_text: str
    ) -> Dict[str, Any]:
        """
        Synthesize a full response with all source information.
        
        Args:
            rag_response: Response from RAG database
            google_response: Response from Google search
            reddit_response: Response from Reddit search
            query_text: Original user query
            
        Returns:
            Dictionary containing final answer and all source responses
        """
        final_answer = self.synthesize_response(
            rag_response, google_response, reddit_response, query_text
        )
        
        return {
            "final_answer": final_answer,
            "rag": rag_response,
            "google": google_response,
            "reddit": reddit_response
        }
