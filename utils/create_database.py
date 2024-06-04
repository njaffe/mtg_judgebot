import os
import shutil
import sys

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import DirectoryLoader

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from config import API_KEY, DATA_PATH, CHROMA_PATH, JSON_DIRECTORY


# def load_documents():
#     """
#     Load documents from the data directory.
#     """
#     loader = DirectoryLoader(DATA_PATH, glob="*.txt")
#     # loader = DirectoryLoader(DATA_PATH)
#     documents = loader.load()
#     print(f"num docs: len(documents)")
#     return documents

def load_documents():
    """
    Load documents from the data directory, supporting both text and JSON formats.
    """
    loader = DirectoryLoader(DATA_PATH,glob="*.txt")
    documents = loader.load()

    json_documents = []
    for filename in os.listdir(JSON_DIRECTORY):
        if filename.endswith('.json'):
            with open(os.path.join(DATA_PATH, filename), 'r') as file:
                data = json.load(file)
                # Assuming each JSON file represents a document
                document = Document(data['content'], metadata=data.get('metadata', {}))
                json_documents.append(document)

    res = documents + json_documents
    print(f"num docs: {len(res)}")
    return res

def split_text(documents: list[Document], verbose=True):
    """
    Split the text into chunks.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=100,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")

    if verbose:
        sample_document = chunks[10]
        print(f"sample document content: {sample_document.page_content}")
        print(f"sample document metadata: {sample_document.metadata}")

    return chunks

def save_to_chroma(chunks: list[Document]):
    """
    Save the chunks to the Chroma database.
    """
    # Remove DB if exists
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    # Create new DB from documents.
    db = Chroma.from_documents(
        chunks,
        OpenAIEmbeddings(openai_api_key=API_KEY),
        persist_directory=CHROMA_PATH
    )
    # db.persist()
    print(f"Saved {len(chunks)} chunks to {CHROMA_PATH}.")

def create_database():
    documents = load_documents()
    chunks = split_text(documents)
    save_to_chroma(chunks)


if __name__ == "__main__":
    create_database()
