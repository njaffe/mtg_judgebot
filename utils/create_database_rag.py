import os
import shutil
import sys
import json  # Added since you use json in the function
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import DirectoryLoader
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))


def load_documents(
    data_path,
    json_directory):
    """
    Load documents from the data directory, supporting both text and JSON formats.
    """
    # Load text documents
    loader = DirectoryLoader(os.path.join(data_path), glob="*.txt")
    documents = loader.load()

    # Load JSON documents
    json_documents = []
    for filename in os.listdir(os.path.join(data_path, json_directory)):
        if filename.endswith('.json'):
            with open(os.path.join(json_directory, filename), 'r') as file:
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


def save_to_chroma(chroma_path, chunks: list[Document], openai_api_key):
    """
    Save the chunks to the Chroma vector database.
    """
    # Remove DB if it exists
    if os.path.exists(chroma_path):
        shutil.rmtree(chroma_path)

    # Create new DB from documents.
    db = Chroma.from_documents(
        chunks,
        OpenAIEmbeddings(openai_api_key=openai_api_key),
        persist_directory=chroma_path
    )
    # Persist the database
    db.persist()
    print(f"Saved {len(chunks)} chunks to {chroma_path}.")


def create_database(
    data_path,
    json_directory,
    chroma_path,
    openai_api_key):
    """
    Full pipeline: Load documents, split text, and save to the Chroma database.
    """
    documents = load_documents(
        data_path,
        json_directory)
    chunks = split_text(documents)
    save_to_chroma(chroma_path, chunks, openai_api_key)


if __name__ == "__main__":
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path)

    openai_api_key = os.getenv('OPENAI_API_KEY')
    chroma_path = os.getenv('CHROMA_PATH')
    data_path = os.getenv('DATA_PATH')
    json_directory = os.getenv('JSON_DIRECTORY')

    print(f"\nCreating database with data_path={data_path}, json_directory={json_directory}, chroma_path={chroma_path}, openai_api_key={openai_api_key[:5]}...\n")

    create_database(
        data_path,
        json_directory,
        chroma_path,
        openai_api_key)