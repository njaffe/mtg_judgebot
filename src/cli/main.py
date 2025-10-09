"""
CLI Main Entry Point for MTG Judge Bot

This module provides the command-line interface for the MTG Judge Bot,
orchestrating queries across multiple sources and synthesizing responses.
"""

import os
import sys
import json
import argparse
from typing import Optional, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Add the parent directory to the path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import our services
from src.core.synthesis_service import SynthesisService
from src.core.rag_service import RAGService
from src.external.google_client import GoogleClient
from src.external.reddit_client import RedditClient
from src.core.indexers import DatabaseIndexer

# Load environment variables
load_dotenv()


class MTGJudgeCLI:
    """
    Command-line interface for the MTG Judge Bot.
    """
    
    def __init__(self):
        """Initialize the CLI with all required services."""
        self.synthesis_service = SynthesisService()
        self.rag_service = RAGService()
        self.google_client = GoogleClient()
        self.reddit_client = RedditClient()
        self.indexer = DatabaseIndexer()
        
        # Test suite path
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.test_file_path = os.path.join(repo_root, 'data', 'tests', 'regression_suite.json')
    
    def refresh_rag_database(self):
        """Refresh the RAG database from raw documents."""
        print("Refreshing RAG database...")
        self.indexer.create_database_from_large_file()
        print("RAG database refreshed successfully!")
    
    def run_single_query(
        self,
        query_text: str,
        subreddit: str = "mtgrules",
        time_filter: str = "year",
        sort: str = "top",
        limit: int = 15
    ) -> Dict[str, Any]:
        """
        Run a single query through all sources and synthesize the response.
        
        Args:
            query_text: The user's query
            subreddit: Reddit subreddit to search
            time_filter: Reddit time filter
            sort: Reddit sort method
            limit: Number of Reddit results
            
        Returns:
            Dictionary containing final answer and all source responses
        """
        print("\nQuerying RAG DB...")
        rag_response = self.rag_service.query(query_text)
        
        print("\nQuerying Google...")
        google_response = self.google_client.search(query_text)
        
        print("\nQuerying Reddit API...")
        reddit_api_response = self.reddit_client.search(
            query_text=query_text,
            subreddit=subreddit,
            time_filter=time_filter,
            sort=sort,
            limit=limit
        )
        
        print("\nQuerying Google (site:reddit.com)...")
        reddit_google_response = self.google_client.search_reddit(query_text)
        
        # Combine Reddit responses
        combined_reddit = f"[Reddit API]\n{reddit_api_response}\n\n[Reddit via Google]\n{reddit_google_response}"
        
        print("\nSynthesizing final answer...")
        final = self.synthesis_service.synthesize_full_response(
            rag_response=rag_response,
            google_response=google_response,
            reddit_response=combined_reddit,
            query_text=query_text
        )
        print(f"Final response: {final['final_answer']}")
    
        usage = final.get("llm_usage", {})
        if usage:
            print(
                f"Usage: total={usage.get('total_tokens', 0)} "
                f"(in {usage.get('prompt_tokens', 0)} / out {usage.get('completion_tokens', 0)}) | "
                f"latency={usage.get('latency_ms', 0)}ms | cost=${usage.get('cost_usd', 0):.6f}"
            )

        return final
    
    def run_test_suite(self, start: Optional[int] = None, end: Optional[int] = None) -> List[Dict]:
        """
        Run the test suite with predefined queries.
        
        Args:
            start: Start index for test suite
            end: End index for test suite
            
        Returns:
            List of test results
        """
        if not os.path.exists(self.test_file_path):
            raise FileNotFoundError(f"Test file not found at {self.test_file_path}")
        
        with open(self.test_file_path, 'r') as file:
            tests = json.load(file)
            if start is not None:
                tests = tests[start:end]
            queries = [test["query"] for test in tests if "query" in test]
        
        if end is None:
            end = len(queries)
        
        if start is not None and (start < 0 or start >= len(queries)):
            raise ValueError("Invalid start index for the test suite.")
        
        responses = []
        for i, query in enumerate(queries[start:end] if start is not None else queries, start=start or 0):
            print(f"\nRunning query {i}: {query}\n")
            response = self.run_single_query(query_text=query)
            print(f"Response: {response['final_answer']}\n")
            print("=" * 80 + "\n")
            responses.append({"query": query, "response": response["final_answer"]})
        
        return responses
    
    def write_results_to_file(self, results: List[Dict], output_file: str):
        """
        Write test results to a JSON file.
        
        Args:
            results: List of test results
            output_file: Output file path
        """
        if not output_file.endswith('.json'):
            raise ValueError("Output file must have a .json extension")
        
        with open(output_file, 'w') as file:
            json.dump(results, file, indent=4)
        print(f"Results written to {output_file}")
    
    def determine_query_text(self, predefined_query: Optional[str] = None, file_path: Optional[str] = None) -> str:
        """
        Determine the query text from various sources.
        
        Args:
            predefined_query: Direct query text
            file_path: Path to file containing query
            
        Returns:
            Query text string
        """
        if predefined_query:
            return predefined_query
        elif file_path and os.path.exists(file_path):
            with open(file_path, 'r') as file:
                return file.read().strip()
        else:
            return input("Please enter your query: ")
    
    def main(
        self,
        query_text: Optional[str] = None,
        file_path: Optional[str] = None,
        test_mode: bool = False,
        refresh_db: bool = False,
        subreddit: str = "mtgrules",
        time_filter: str = "year",
        sort: str = "top",
        limit: int = 15,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ):
        """
        Main entry point for the CLI.
        
        Args:
            query_text: Direct query text
            file_path: Path to file with query
            test_mode: Run in test mode
            refresh_db: Refresh the RAG database
            subreddit: Reddit subreddit to search
            time_filter: Reddit time filter
            sort: Reddit sort method
            limit: Number of Reddit results
            start: Start index for test suite
            end: End index for test suite
        """
        if refresh_db:
            self.refresh_rag_database()
        
        if test_mode:
            print("\nRunning in test mode with predefined queries...\n")
            results = self.run_test_suite(start, end)
            today_date = datetime.now().strftime("%Y-%m-%d")
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            output_file = os.path.join(repo_root, 'data', 'tests', f'test_results_{today_date}.json')
            self.write_results_to_file(results, output_file)
        else:
            print("\nRunning single query...\n")
            query_text = query_text or self.determine_query_text(file_path=file_path)
            result = self.run_single_query(
                query_text=query_text,
                subreddit=subreddit,
                time_filter=time_filter,
                sort=sort,
                limit=limit
            )
            print("\nFinal Synthesized Response:\n", result["final_answer"])
            return result


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Run MTG Query Pipeline")
    parser.add_argument("--query_text", type=str, help="The query text.")
    parser.add_argument("--file_path", type=str, help="Path to a file with the query.")
    parser.add_argument("--test_mode", action="store_true", help="Run test suite instead of single query.")
    parser.add_argument("--refresh_db", action="store_true", help="Refresh RAG database.")
    parser.add_argument("--subreddit", type=str, default="mtgrules")
    parser.add_argument("--time_filter", type=str, 
                       choices=["hour", "day", "week", "month", "year", "all"], 
                       default="year")
    parser.add_argument("--sort", type=str, 
                       choices=["relevance", "hot", "top", "new", "comments"], 
                       default="top")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--start", type=int, help="Start index for test suite.")
    parser.add_argument("--end", type=int, help="End index for test suite.")
    
    args = parser.parse_args()
    
    cli = MTGJudgeCLI()
    cli.main(
        query_text=args.query_text,
        file_path=args.file_path,
        test_mode=args.test_mode,
        refresh_db=args.refresh_db,
        subreddit=args.subreddit,
        time_filter=args.time_filter,
        sort=args.sort,
        limit=args.limit,
        start=args.start,
        end=args.end
    )


if __name__ == "__main__":
    main()

## example usage: python src/cli/main.py --query_text "What happens when a creature dies?"