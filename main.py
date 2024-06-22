import os
import sys

# from src.convert_to_md import process_inputs_in_directory
# from src.create_database import create_database
# from src.query_database import query_database
# from src.query_reddit import query_reddit

from utils.query_tools import create_prompt, run_query

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from config import API_KEY, DATA_PATH, CHROMA_PATH


def main():
    # process_inputs_in_directory()
    # create_database()
    query_database_rag()
    query_reddit()
    query_google()

    # what if reddit and database disagree? 

if __name__ == "__main__":
    main()