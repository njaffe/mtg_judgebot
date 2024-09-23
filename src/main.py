from query_tools.query_database_rag import query_rag_db
from query_tools.query_google import query_google
from query_tools.query_reddit import query_reddit
from utils.create_database_rag import create_database  # Add this import

def run_queries(refresh_db=False):
    # Optionally refresh the RAG database
    if refresh_db:
        create_database()

    # Example usage
    result_rag = query_rag_db()
    result_google = query_google()
    result_reddit = query_reddit()

    # Combine and process results if necessary
    return result_rag, result_google, result_reddit

if __name__ == "__main__":
    # Pass `refresh_db=True` to refresh the database before querying
    results = run_queries(refresh_db=False)
    print(results)