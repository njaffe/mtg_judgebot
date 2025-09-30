# Makefile

.PHONY: install run refresh-db

# Install Python dependencies
install:
	pip install -r requirements.txt

# Run the main query script
run:
	python src/main.py

# Refresh the RAG database (rebuild FAISS index)
refresh-db:
	python src/create_database_rag.py

# Run with CLI args (example query)
run-query:
	python src/main.py --query_text "What are the latest Magic: The Gathering tournament rules?"

# Run with a query file (replace query.txt with your actual file)
run-file:
	python src/main.py --file_path data/query.txt