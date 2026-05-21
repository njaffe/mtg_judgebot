"""
CLI Main Entry Point for MTG Judge Bot

This module provides the command-line interface for the MTG Judge Bot,
orchestrating queries across multiple sources and synthesizing responses.
"""

import os
import sys
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Add the parent directory to the path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import our services
from src.core.synthesis_service import SynthesisService
from src.core.rag_service import RAGService
from src.core.indexers import DatabaseIndexer
from src.external.scryfall_client import ScryfallClient

# Load environment variables
load_dotenv()

# External sources are off by default
ENABLE_EXTERNAL_SOURCES = os.getenv("ENABLE_EXTERNAL_SOURCES", "false").lower() == "true"


def _init_external_clients():
    """Lazily initialize Google and Reddit clients (only when needed)."""
    from src.external.google_client import GoogleClient
    from src.external.reddit_client import RedditClient
    return GoogleClient(), RedditClient()


class MTGJudgeCLI:
    """
    Command-line interface for the MTG Judge Bot.
    """

    def __init__(self):
        """Initialize the CLI with required services."""
        self.synthesis_service = SynthesisService()
        self.rag_service = RAGService()
        self.scryfall_client = ScryfallClient()
        self.indexer = DatabaseIndexer()

        # External clients initialized lazily
        self._google_client = None
        self._reddit_client = None

        # Test suite path
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.test_file_path = os.path.join(repo_root, 'src', 'data', 'tests', 'regression_suite.json')

    def _get_external_clients(self):
        """Get or initialize external clients."""
        if self._google_client is None:
            self._google_client, self._reddit_client = _init_external_clients()
        return self._google_client, self._reddit_client

    def refresh_rag_database(self):
        """Refresh the RAG database from raw documents."""
        print("Refreshing RAG database...")
        self.indexer.create_database_from_large_file()
        print("RAG database refreshed successfully!")

    def run_single_query(
        self,
        query_text: str,
        enable_external: Optional[bool] = None,
        subreddit: str = "mtgrules",
        time_filter: str = "year",
        sort: str = "top",
        limit: int = 15,
    ) -> Dict[str, Any]:
        """
        Run a single query through all sources and synthesize the response.

        Args:
            query_text: The user's query
            enable_external: Override for external sources (None = use env default)
            subreddit: Reddit subreddit to search
            time_filter: Reddit time filter
            sort: Reddit sort method
            limit: Number of Reddit results

        Returns:
            Dictionary containing final answer and all source responses
        """
        use_external = enable_external if enable_external is not None else ENABLE_EXTERNAL_SOURCES

        # Phase 1: Parallel data gathering
        card_data_str = ""
        rag_response = ""
        google_response = None
        reddit_response = None

        with ThreadPoolExecutor(max_workers=4) as executor:
            # Always run: Scryfall card lookup + RAG
            future_scryfall = executor.submit(self._lookup_cards, query_text)
            # We need card_data for the RAG prompt, so we get it first
            # then submit RAG — but to maximize parallelism, we start RAG
            # without card data and the synthesis will have it anyway.
            # Actually, let's do card lookup first since it's fast (~200ms),
            # then pass card_data to RAG.

        # Step 1: Card lookup (fast, ~200ms)
        print("\nLooking up cards on Scryfall...")
        cards = self.scryfall_client.lookup_cards(query_text)
        card_data_str = ScryfallClient.format_card_data(cards)
        if cards:
            print(f"  Found {len(cards)} card(s): {', '.join(c['name'] for c in cards)}")
        else:
            print("  No specific cards identified in query.")

        # Step 2: Parallel — RAG (with card data) + optional external sources
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}

            print("\nQuerying RAG DB...")
            futures["rag"] = executor.submit(self.rag_service.query, query_text, card_data_str)

            if use_external:
                google_client, reddit_client = self._get_external_clients()
                print("Querying Google...")
                futures["google"] = executor.submit(google_client.search, query_text)
                print("Querying Reddit API...")
                futures["reddit_api"] = executor.submit(
                    reddit_client.search,
                    query_text=query_text,
                    subreddit=subreddit,
                    time_filter=time_filter,
                    sort=sort,
                    limit=limit,
                )
                print("Querying Google (site:reddit.com)...")
                futures["reddit_google"] = executor.submit(google_client.search_reddit, query_text)

            # Collect results
            for key, future in futures.items():
                try:
                    result = future.result(timeout=120)
                    if key == "rag":
                        rag_response = result
                    elif key == "google":
                        google_response = result
                    elif key == "reddit_api":
                        reddit_api = result
                    elif key == "reddit_google":
                        reddit_google = result
                except Exception as e:
                    print(f"  Warning: {key} failed: {e}")

        # Combine Reddit responses if external sources are enabled
        if use_external and (google_response or reddit_response):
            reddit_parts = []
            if 'reddit_api' in locals() and reddit_api:
                reddit_parts.append(f"[Reddit API]\n{reddit_api}")
            if 'reddit_google' in locals() and reddit_google:
                reddit_parts.append(f"[Reddit via Google]\n{reddit_google}")
            if reddit_parts:
                reddit_response = "\n\n".join(reddit_parts)

        # Phase 2: Synthesis
        print("\nSynthesizing final answer...")
        final = self.synthesis_service.synthesize_full_response(
            rag_response=rag_response,
            query_text=query_text,
            card_data=card_data_str,
            google_response=google_response,
            reddit_response=reddit_response,
        )
        print(f"Final response: {final['final_answer'][:200]}...")

        usage = final.get("llm_usage", {})
        if usage:
            print(
                f"Usage: total={usage.get('total_tokens', 0)} "
                f"(in {usage.get('prompt_tokens', 0)} / out {usage.get('completion_tokens', 0)}) | "
                f"latency={usage.get('latency_ms', 0)}ms | cost=${usage.get('cost_usd', 0):.6f}"
            )

        return final

    def _lookup_cards(self, query_text: str) -> List[Dict[str, Any]]:
        """Look up cards mentioned in the query via Scryfall."""
        return self.scryfall_client.lookup_cards(query_text)

    def run_test_suite(self, start: Optional[int] = None, end: Optional[int] = None) -> List[Dict]:
        """Run the test suite with predefined queries."""
        if not os.path.exists(self.test_file_path):
            raise FileNotFoundError(f"Test file not found at {self.test_file_path}")

        with open(self.test_file_path, 'r') as file:
            tests = json.load(file)
            queries = [test["query"] for test in tests if "query" in test]

        # Apply slice
        actual_start = start or 0
        actual_end = end or len(queries)
        selected = queries[actual_start:actual_end]

        responses = []
        for i, query in enumerate(selected, start=actual_start):
            print(f"\nRunning query {i}: {query}\n")
            response = self.run_single_query(query_text=query)
            print(f"Response: {response['final_answer']}\n")
            print("=" * 80 + "\n")
            responses.append({"query": query, "response": response["final_answer"]})

        return responses

    def write_results_to_file(self, results: List[Dict], output_file: str):
        """Write test results to a JSON file."""
        if not output_file.endswith('.json'):
            raise ValueError("Output file must have a .json extension")

        with open(output_file, 'w') as file:
            json.dump(results, file, indent=4)
        print(f"Results written to {output_file}")

    def determine_query_text(self, predefined_query: Optional[str] = None, file_path: Optional[str] = None) -> str:
        """Determine the query text from various sources."""
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
        enable_external: Optional[bool] = None,
        subreddit: str = "mtgrules",
        time_filter: str = "year",
        sort: str = "top",
        limit: int = 15,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ):
        """Main entry point for the CLI."""
        if refresh_db:
            self.refresh_rag_database()

        if test_mode:
            print("\nRunning in test mode with predefined queries...\n")
            results = self.run_test_suite(start, end)
            today_date = datetime.now().strftime("%Y-%m-%d")
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            output_file = os.path.join(repo_root, 'src', 'data', 'tests', f'test_results_{today_date}.json')
            self.write_results_to_file(results, output_file)
        else:
            print("\nRunning single query...\n")
            query_text = query_text or self.determine_query_text(file_path=file_path)
            result = self.run_single_query(
                query_text=query_text,
                enable_external=enable_external,
                subreddit=subreddit,
                time_filter=time_filter,
                sort=sort,
                limit=limit,
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
    parser.add_argument("--enable_external", action="store_true",
                        help="Enable Google/Reddit external sources (off by default).")
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
        enable_external=args.enable_external if args.enable_external else None,
        subreddit=args.subreddit,
        time_filter=args.time_filter,
        sort=args.sort,
        limit=args.limit,
        start=args.start,
        end=args.end,
    )


if __name__ == "__main__":
    main()

## example usage: python src/cli/main.py --query_text "What happens when a creature dies?"
## with external sources: python src/cli/main.py --query_text "..." --enable_external
