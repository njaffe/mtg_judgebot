import os

PDF_DIRECTORY = os.getenv("PDF_DIRECTORY", "default_pdf_dir")
PDF_DIRECTORY='data/pdfs'
MARKDOWN_DIRECTORY = os.getenv("MARKDOWN_DIRECTORY", "default_markdown_dir")
API_KEY = os.environ["OPENAI_API_KEY"]
DATA_PATH = "data" # adds mtg_rules.txt to db
JSON_DIRECTORY = "data/jsons"
CHROMA_PATH = "chroma"
MARKDOWN_DIRECTORY='data/markdowns'
PROMPT_TEMPLATE = """
        Answer the question based on the following context:

        {context_text}
        ---

        Answer the question based on the above context: {query}
    """