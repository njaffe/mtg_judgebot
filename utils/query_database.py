import argparse
import os
import sys

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from config import API_KEY, CHROMA_PATH, PROMPT_TEMPLATE


def load_args_db():
    # CLI arg parsing
    parser = argparse.ArgumentParser(description="Query the database.")
    parser.add_argument("query_text", type=str, help="Query text.")
    args = parser.parse_args()
    query_text = args.query_text

    # Load the database
    embedding_function = OpenAIEmbeddings(openai_api_key=API_KEY)
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    return query_text, db

def create_context_and_prompt(query_text, db, show_similarity=False):
    """
    Create the context and prompt for the query.
    """

    # Create context
    print("\nCreating context.\n")
    # Method 1: Simple similarity search
    context_results = db.similarity_search(query_text)
    context_text = "\n\n---\n\n".join([doc.page_content for doc in context_results])

    # Method 2: Search with relevance scores
    context_results_with_sim = db.similarity_search_with_relevance_scores(query_text, k=3)
    if len(context_results_with_sim) == 0 or context_results_with_sim[0][1] < 0.7:
        print("No results found.")
        return
    context_text_sim = "\n\n---\n\n".join([doc.page_content for doc, _score in context_results_with_sim])
    
    # Create prompt
    print("\nCreating prompt.\n")  
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    if show_similarity:
        prompt = prompt_template.format(context_text=context_text_sim, query=query_text)
    else:
        prompt = prompt_template.format(context_text=context_text, query=query_text)
    return prompt

def query_database(verbose=False):
    """
    Query the database.
    """
    # Load the query text and database
    query_text, db = load_args_db()

    # Create context and prompt
    prompt = create_context_and_prompt(query_text, db)

    # Define LLM
    model = ChatOpenAI()

    if verbose:
        # print(f"\nQuerying the database with the following prompt:\n\n{prompt}\n")
        print(f"\nQuerying the database with the following query:\n\n{query_text}\n")

    # Query LLM
    response_text = model.invoke(prompt).content
    print(f"\n{response_text}\n")

if __name__ == "__main__":
    query_database()