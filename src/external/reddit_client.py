"""
Reddit Client Service for MTG Judge Bot

This module provides a service class for Reddit API integration.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class RedditClient:
    """
    Service class for Reddit API integration.
    """
    
    def __init__(self,
                 reddit_client_id: Optional[str] = None,
                 reddit_client_secret: Optional[str] = None,
                 reddit_user_agent: Optional[str] = None,
                 openai_api_key: Optional[str] = None):
        """
        Initialize the Reddit client.
        
        Args:
            reddit_client_id: Reddit client ID
            reddit_client_secret: Reddit client secret
            reddit_user_agent: Reddit user agent
            openai_api_key: OpenAI API key for summarization
        """
        self.reddit_client_id = reddit_client_id or os.getenv("REDDIT_CLIENT_ID")
        self.reddit_client_secret = reddit_client_secret or os.getenv("REDDIT_CLIENT_SECRET")
        self.reddit_user_agent = reddit_user_agent or os.getenv("REDDIT_USER_AGENT")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        if not all([self.reddit_client_id, self.reddit_client_secret, 
                   self.reddit_user_agent, self.openai_api_key]):
            raise ValueError("Reddit API credentials and OpenAI API key are required")
    
    def search(self, 
               query_text: str,
               subreddit: str = "mtgrules",
               time_filter: str = "year",
               sort: str = "top",
               limit: int = 15) -> str:
        """
        Search Reddit and return summarized results.
        
        Args:
            query_text: The search query
            subreddit: Reddit subreddit to search
            time_filter: Reddit time filter
            sort: Reddit sort method
            limit: Number of results
            
        Returns:
            Summarized Reddit search results
        """
        import requests
        from openai import OpenAI
        
        # Perform Reddit search
        auth = requests.auth.HTTPBasicAuth(self.reddit_client_id, self.reddit_client_secret)
        data = {'grant_type': 'client_credentials'}
        headers = {'User-Agent': self.reddit_user_agent}

        res = requests.post('https://www.reddit.com/api/v1/access_token', auth=auth, data=data, headers=headers)
        token = res.json().get('access_token')
        if not token:
            raise Exception(f"Could not retrieve Reddit token: {res.text}")

        headers['Authorization'] = f'bearer {token}'

        params = {
            'q': query_text,
            'limit': limit,
            'sort': sort or 'relevance',
            't': time_filter or 'all',
            'restrict_sr': False,
        }

        url = f"https://oauth.reddit.com/r/{subreddit}/search" if subreddit else "https://oauth.reddit.com/search"
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            raise Exception(f"Reddit API call failed: {response.text}")

        json_data = response.json()
        results = [child['data'] for child in json_data.get('data', {}).get('children', [])]
        
        if not results:
            return "No Reddit posts found for the query."
        
        # Process Reddit Results into a summary text
        reddit_summary = ""
        max_summary_length = 3000
        for idx, post_data in enumerate(results, 1):
            post_summary = f"{idx}. {post_data.get('title', '')}\n{post_data.get('selftext', '')[:300]}...\n\n"
            if len(reddit_summary) + len(post_summary) > max_summary_length:
                break
            reddit_summary += post_summary

        # Compose prompt
        prompt = (
            f"You are an expert in analyzing Reddit discussions.\n\n"
            f"Here are some posts retrieved based on the query:\n\n{reddit_summary}\n\n"
            f"Given the above posts, answer the following query:\n\n{query_text}\n\n"
        )

        # Call OpenAI Chat Model
        client = OpenAI(api_key=self.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.5
        )

        return response.choices[0].message.content