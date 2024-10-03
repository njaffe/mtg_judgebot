import os
import sys
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from config import API_KEY, CHROMA_PATH, PROMPT_TEMPLATE

def load_db():
    """
    Load the RAG database.
    """
    embedding_function = OpenAIEmbeddings(openai_api_key=API_KEY)
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    return db

def load_query_text(query_text=None, file_path=None):
    """
    Load query text either from a string or a text file.
    If both are provided, it will prioritize the string input.
    """
    if query_text:
        return query_text
    elif file_path and os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return file.read().strip()
    else:
        raise ValueError("Either query_text or a valid file_path must be provided.")

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
        return "No relevant context found."
    context_text_sim = "\n\n---\n\n".join([doc.page_content for doc, _score in context_results_with_sim])
    
    # Create prompt
    print("\nCreating prompt.\n")  
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    
    if show_similarity:
        prompt = prompt_template.format(context_text=context_text_sim, query=query_text)
    else:
        prompt = prompt_template.format(context_text=context_text, query=query_text)
    
    return prompt

def query_rag_db(query_text=None, file_path=None, verbose=False):
    """
    Query the RAG database.
    """
    # Load the query text from string or file
    query_text = load_query_text(query_text=query_text, file_path=file_path)

    # Load the database
    db = load_db()

    # Create context and prompt
    prompt = create_context_and_prompt(query_text, db)

    # Define LLM
    model = ChatOpenAI()

    if verbose:
        print(f"\nQuerying the database with the following query:\n\n{query_text}\n")
        print(f"\nGenerated prompt:\n\n{prompt}\n")

    # Query LLM
    response_text = model.invoke(prompt).content
    print(f"\n{response_text}\n")

    return response_text

if __name__ == "__main__":
    # For command line usage, specify either a string or a file
    import argparse

    parser = argparse.ArgumentParser(description="Query the RAG database with a string or text file.")
    parser.add_argument("--query_text", type=str, help="The text query to be used.")
    parser.add_argument("--file_path", type=str, help="Path to the file containing the query.")
    parser.add_argument("--verbose", action='store_true', help="Print detailed information.")

    args = parser.parse_args()

    # Ensure either query_text or file_path is provided
    if not args.query_text and not args.file_path:
        raise ValueError("Either --query_text or --file_path must be provided.")

    # Run the RAG DB query
    query_rag_db(query_text=args.query_text, file_path=args.file_path, verbose=args.verbose)

# python utils/query_database_rag.py --query_text "I have a creature with the following text: Whenever Ghost of Ramirez DePietro deals combat damage to a player, choose up to one target card in a graveyard that was discarded or put there from a library this turn. Put that card into its owner's hand. I have another creature with the text: 'Whenever one or more Pirates you control deal damage to a player, Francisco explores.' Can I return a card put into my graveyard by the explore ability with the first ability? Ramirez is a pirate."
