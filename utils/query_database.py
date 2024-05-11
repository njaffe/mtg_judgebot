import argparse
import os
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

api_key = os.environ["OPENAI_API_KEY"]
CHROMA_PATH = "chroma"
PROMPT_TEMPLATE = """
        Answer the question based on the following context:

        {context_text}
        ---

        Answer the question based on the above context: {query}
    """

def load_args_db():
    # CLI arg parsing
    parser = argparse.ArgumentParser(description="Query the database.")
    parser.add_argument("query_text", type=str, help="Query text.")
    args = parser.parse_args()
    query_text = args.query_text

    # Load the database
    embedding_function = OpenAIEmbeddings(openai_api_key=api_key)
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    return db, query_text

def create_context_and_prompt(db, query_text, similarity=False):
    print("Querying database")

    # Create context
    
    # Method 1: Simple similarity search
    context_results = db.similarity_search(query_text)
    # print(f"doc 1 metadata: {results[0].metadata}")
    # print(f"{results[0].page_content}")
    context_text = "\n\n---\n\n".join([doc.page_content for doc in context_results])
    # print(context_text)

    # Method 2: Search with relevance scores
    context_results_with_sim = db.similarity_search_with_relevance_scores(query_text, k=3)
    if len(context_results_with_sim) == 0 or context_results_with_sim[0][1] < 0.7:
        print("No results found.")
        return
    context_text_sim = "\n\n---\n\n".join([doc.page_content for doc, _score in context_results_with_sim])
    # print(context_text_sim)
    
    # Create prompt
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    if similarity:
        prompt = prompt_template.format(context_text=context_text_sim, query=query_text)
    else:
        prompt = prompt_template.format(context_text=context_text, query=query_text)
    return prompt


def query_database():
    db, query_text = load_args_db()
    prompt = create_context_and_prompt(db, query_text)

    model = ChatOpenAI()
    response_text = model.invoke(prompt)
    print(f"\n{response_text}\n")

if __name__ == "__main__":
    query_database()