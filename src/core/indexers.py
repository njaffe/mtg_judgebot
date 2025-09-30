"""
Database Indexers for MTG Judge Bot

This module provides service classes for database indexing operations using FAISS.
"""

import os
import shutil
import pickle
import faiss
import numpy as np
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseIndexer:
    """
    Service class for database indexing operations using FAISS.
    """
    
    def __init__(self,
                 openai_api_key: Optional[str] = None,
                 faiss_index_path: Optional[str] = None,
                 data_path: Optional[str] = None,
                 raw_docs_path: Optional[str] = None):
        """
        Initialize the database indexer.
        
        Args:
            openai_api_key: OpenAI API key
            faiss_index_path: Path to FAISS index
            data_path: Path to data directory
            raw_docs_path: Path to raw documents
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.faiss_index_path = faiss_index_path or os.getenv("FAISS_INDEX_PATH")
        self.data_path = data_path or os.getenv("DATA_PATH")
        self.raw_docs_path = raw_docs_path or os.getenv("RAW_DOCS_PATH")
        
        if not all([self.openai_api_key, self.faiss_index_path, 
                   self.data_path, self.raw_docs_path]):
            raise ValueError("All database configuration parameters are required")
        
        self.client = OpenAI(api_key=self.openai_api_key)
    
    def _load_single_large_text_file(self, file_path):
        """
        Load a single large text file.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        document = {
            'content': content,
            'metadata': {'filename': os.path.basename(file_path)}
        }
        print(f"Loaded file: {file_path} with {len(content)} characters.")
        return [document]
    
    def _split_text(self, documents, chunk_size=300, chunk_overlap=100, verbose=True):
        """
        Split documents into smaller chunks.
        """
        chunks = []
        for doc in documents:
            text = doc['content']
            metadata = doc['metadata']
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk_text = text[start:end]
                chunks.append({
                    'content': chunk_text,
                    'metadata': metadata
                })
                start += chunk_size - chunk_overlap

        print(f"Split {len(documents)} document(s) into {len(chunks)} chunks.")

        if verbose and chunks:
            sample = chunks[min(10, len(chunks) - 1)]
            print(f"Sample chunk content: {sample['content'][:200]}...")
            print(f"Sample chunk metadata: {sample['metadata']}")

        return chunks
    
    def _embed_texts(self, texts):
        """
        Embed a list of texts using OpenAI's Embedding API.
        """
        embeddings = []
        batch_size = 1000
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            response = self.client.embeddings.create(
                input=batch,
                model="text-embedding-ada-002"
            )
            batch_embeddings = [np.array(item.embedding, dtype=np.float32) for item in response.data]
            embeddings.extend(batch_embeddings)

        return embeddings
    
    def _save_to_faiss(self, documents):
        """
        Save documents and embeddings to a FAISS index.
        """
        if os.path.exists(self.faiss_index_path):
            shutil.rmtree(self.faiss_index_path)
        os.makedirs(self.faiss_index_path, exist_ok=True)

        texts = [doc['content'] for doc in documents]
        embeddings = self._embed_texts(texts)

        dim = len(embeddings[0])
        index = faiss.IndexFlatL2(dim)
        index.add(np.vstack(embeddings))

        # Save FAISS index
        faiss.write_index(index, os.path.join(self.faiss_index_path, "faiss.index"))

        # Save documents
        with open(os.path.join(self.faiss_index_path, "documents.pkl"), 'wb') as f:
            pickle.dump(documents, f)

        print(f"Saved {len(documents)} chunks and embeddings to {self.faiss_index_path}.")
    
    def create_database_from_large_file(self):
        """
        Create database from large text file.
        """
        # Find the first .txt file in raw_docs
        files = [f for f in os.listdir(os.path.join(self.data_path, self.raw_docs_path)) 
                if f.endswith('.txt')]
        if not files:
            raise FileNotFoundError(f"No .txt files found in {self.raw_docs_path}")
        
        large_text_file_path = os.path.join(self.data_path, self.raw_docs_path, files[0])
        
        print(f"Creating FAISS database from {large_text_file_path} into {self.faiss_index_path}...")
        
        # Load the document
        documents = self._load_single_large_text_file(large_text_file_path)
        
        # Split into chunks
        chunks = self._split_text(documents)
        
        # Save to FAISS
        self._save_to_faiss(chunks)
        
        print("Database creation completed successfully!")