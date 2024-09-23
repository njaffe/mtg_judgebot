import os
import shutil
import sys
import json  # Added since you use json in the function
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import DirectoryLoader

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from config import API_KEY, DATA_PATH, CHROMA_PATH, JSON_DIRECTORY


def load_documents():
    """
    Load documents from the data directory, supporting both text and JSON formats.
    """
    # Load text documents
    loader = DirectoryLoader(DATA_PATH, glob="*.txt")
    documents = loader.load()

    # Load JSON documents
    json_documents = []
    for filename in os.listdir(JSON_DIRECTORY):
        if filename.endswith('.json'):
            with open(os.path.join(JSON_DIRECTORY, filename), 'r') as file:  # Fix path to JSON_DIRECTORY
                try:
                    data = json.load(file)
                    document = Document(data['content'], metadata=data.get('metadata', {}))
                    json_documents.append(document)
                except KeyError as e:
                    print(f"Error processing {filename}: Missing key {e}")
                except json.JSONDecodeError:
                    print(f"Error decoding JSON file {filename}")

    res = documents + json_documents
    print(f"Loaded {len(res)} documents.")
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
        sample_document = chunks[10] if len(chunks) > 10 else chunks[0]
        print(f"Sample document content: {sample_document.page_content}")
        print(f"Sample document metadata: {sample_document.metadata}")

    return chunks


def save_to_chroma(chunks: list[Document]):
    """
    Save the chunks to the Chroma vector database.
    """
    # Remove DB if it exists
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    # Create new DB from documents.
    db = Chroma.from_documents(
        chunks,
        OpenAIEmbeddings(openai_api_key=API_KEY),
        persist_directory=CHROMA_PATH
    )
    # Persist the database
    db.persist()
    print(f"Saved {len(chunks)} chunks to {CHROMA_PATH}.")


def create_database():
    """
    Full pipeline: Load documents, split text, and save to the Chroma database.
    """
    documents = load_documents()
    chunks = split_text(documents)
    save_to_chroma(chunks)


if __name__ == "__main__":
    create_database()