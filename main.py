import os
import sys

from utils.convert_to_md import process_inputs_in_directory
from utils.create_database import create_database
from utils.query_database import query_database
from utils.query_reddit import query_reddit

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from config import API_KEY, DATA_PATH, CHROMA_PATH


def main():
    process_inputs_in_directory()
    create_database()
    query_database()
    query_reddit()

    # what if reddit and database disagree? 

if __name__ == "__main__":
    main()