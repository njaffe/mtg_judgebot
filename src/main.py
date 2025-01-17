import os
import sys
from dotenv import load_dotenv

# Add paths for utilities and source files
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from query_database_rag import query_rag_db
from query_google import query_google
from query_reddit import query_reddit
from create_database_rag import create_database

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

# Define API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

def run_queries(query_text, refresh_db=False, subreddit=None, time_filter=None, sort=None, limit=10):
    """
    Run queries on RAG DB, Google Search, and Reddit Search.
    Optionally refresh the RAG DB before querying.

    Args:
        query_text (str): The input query to run.
        refresh_db (bool): Whether to refresh the RAG database before querying.
        subreddit (str): Subreddit to filter results (for Reddit query).
        time_filter (str): Time filter for Reddit results (e.g., 'day', 'week').
        sort (str): Sorting order for Reddit results (e.g., 'new', 'top').
        limit (int): Maximum number of Reddit results to retrieve.

    Returns:
        str: Combined results from all queries in formatted string.
    """
    if refresh_db:
        print("\nRefreshing the RAG database...\n")
        create_database()

    # Query RAG database
    print("\nQuerying the RAG database...\n")
    result_rag = query_rag_db(query_text=query_text)

    # Query Google Search
    print("\nQuerying Google Search...\n")
    result_google = query_google(
        openai_api_key=OPENAI_API_KEY, 
        google_cse_id=GOOGLE_CSE_ID, 
        google_api_key=GOOGLE_API_KEY, 
        query_text=query_text
    )

    # Query Reddit Search
    print("\nQuerying Reddit Search...\n")
    result_reddit = query_reddit(
        openai_api_key=OPENAI_API_KEY,
        reddit_client_id=REDDIT_CLIENT_ID,
        reddit_client_secret=REDDIT_CLIENT_SECRET,
        reddit_user_agent=REDDIT_USER_AGENT,
        query_text=query_text,
        subreddit=subreddit,
        time_filter=time_filter,
        sort=sort,
        limit=limit
    )

    # Combine results from all sources
    combined_results_dict = {
        "RAG_DB_Result": result_rag,
        "Google_Search_Result": result_google,
        "Reddit_Search_Result": result_reddit,
    }

    # Format combined results as a paragraph
    combined_results = "\n\n".join([f"**{key}**:\n{value}" for key, value in combined_results_dict.items()])
    return combined_results

def determine_query_text(predefined_query=None, file_path=None):
    """
    Determine the query text from a predefined query, file, or user input.

    Args:
        predefined_query (str): Predefined query text for testing purposes.
        file_path (str): Path to a file containing the query text.

    Returns:
        str: The final query text to use.
    """
    if predefined_query:
        return predefined_query
    elif file_path and os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return file.read().strip()
    else:
        return input("Please enter your query: ")

if __name__ == "__main__":
    import argparse

    # Default variables for testing or non-CLI usage
    DEFAULT_SUBREDDIT = "mtgrules"
    DEFAULT_TIME_FILTER = "year"
    DEFAULT_SORT = "top"
    DEFAULT_LIMIT = 5
    PREDEFINED_QUERY = """I have a creature with the following text: Whenever Ghost of Ramirez DePietro deals combat damage to a player, choose up to one target card in a graveyard that was discarded or put there from a library this turn. Put that card into its owner's hand. I have another creature with the text: 'Whenever one or more Pirates you control deal damage to a player, Francisco explores.' Can I return a card put into my graveyard by the explore ability with the first ability? Ramirez is a pirate."""

    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="Query multiple sources with a string or file.")
    parser.add_argument("--query_text", type=str, help="The text query to be used.")
    parser.add_argument("--file_path", type=str, help="Path to the file containing the query.")
    parser.add_argument("--refresh_db", action="store_true", help="Refresh the RAG database before querying.")
    parser.add_argument("--subreddit", type=str, help="The subreddit to filter Reddit results.")
    parser.add_argument("--time_filter", type=str, choices=["hour", "day", "week", "month", "year", "all"], help="The time filter for Reddit results.")
    parser.add_argument("--sort", type=str, choices=["relevance", "hot", "top", "new", "comments"], help="The sorting order for Reddit results.")
    parser.add_argument("--limit", type=int, help="The maximum number of Reddit results to retrieve.")

    args = parser.parse_args()

    # Use CLI inputs if provided, otherwise fall back to defaults
    query_text = args.query_text or determine_query_text(predefined_query=PREDEFINED_QUERY, file_path=args.file_path)
    subreddit = args.subreddit or DEFAULT_SUBREDDIT
    time_filter = args.time_filter or DEFAULT_TIME_FILTER
    sort = args.sort or DEFAULT_SORT
    limit = args.limit or DEFAULT_LIMIT

    # Run queries
    results = run_queries(
        query_text=query_text,
        refresh_db=args.refresh_db,
        subreddit=subreddit,
        time_filter=time_filter,
        sort=sort,
        limit=limit
    )

    # Print combined results
    print("\nCombined Results:\n", results)

# python src/main.py

# both query_redit and query_google appear to be working as expected, but function here is failing