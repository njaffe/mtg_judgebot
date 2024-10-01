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

# Define API keys and environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT")

def run_queries(query_text, refresh_db=False):
    """
    Run queries on RAG DB, Google Search, and Reddit Search.
    Optionally refresh the RAG DB before querying.
    """

    # Optionally refresh the RAG database
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
        query_text=query_text
    )

    # Combine results from all sources
    combined_results_dict = {
        "RAG_DB_Result": result_rag,
        "Google_Search_Result": result_google,
        "Reddit_Search_Result": result_reddit,
    }

    # Return combined results as paragraph:

    combined_results = "\n\n".join([f"**{key}**:\n{value}" for key, value in combined_results_dict.items()])

    
    return combined_results

if __name__ == "__main__":
    import argparse

    # Example query text
    sample_query_text = """I have a creature with the following text: 
        Whenever Ghost of Ramirez DePietro deals combat damage to a player, 
        choose up to one target card in a graveyard that was discarded or put there from a library this turn. 
        Put that card into its owner's hand. I have another creature with the text: 
        'Whenever one or more Pirates you control deal damage to a player, Francisco explores.' 
        Can I return a card put into my graveyard by the explore ability with the first ability? 
        Ramirez is a pirate."""

    # sample_query_text = """I am a 30 year old male and I would like to lose weight. I weight 
    # 200 lbs and I am 6 feet tall. I would like to know how many calories I should eat per day
    # to lose weight. I would also like to know how much protein I should be getting per day."""


    # CLI argument parsing
    parser = argparse.ArgumentParser(description="Query Reddit with a string or file.")
    parser.add_argument("--query_text", type=str, help="The text query to be used.")
    parser.add_argument("--file_path", type=str, help="Path to the file containing the query.")

    args = parser.parse_args()

    # Ensure either query_text or file_path is provided
    if not args.query_text and not args.file_path:
        if sample_query_text:
            print("No --query_text or --file_path provided; using sample.")
            query_text = sample_query_text
        else:
            raise ValueError("No --query_text, --file_path or sample provided.")
        


    # Run all queries and combine results
    results = run_queries(query_text=query_text, refresh_db=False)

    # Print combined results
    print("\nCombined Results:\n", results)

# python src/main.py

# both query_redit and query_google appear to be working as expected, but function here is failing