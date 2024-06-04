import os

API_KEY = os.environ["OPENAI_API_KEY"]
DATA_PATH = "data" # adds mtg_rules.txt to db
JSON_DIRECTORY = "data/jsons"
CHROMA_PATH = "chroma"
PDF_DIRECTORY='data/pdfs'
MARKDOWN_DIRECTORY='data/markdowns'
PROMPT_TEMPLATE = """
        Answer the question based on the following context:

        {context_text}
        ---

        Answer the question based on the above context: {query}
    """