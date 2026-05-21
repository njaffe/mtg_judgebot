.PHONY: setup run test index update-rules ui

# First-time setup: create venv and install dependencies
setup:
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
	@echo "\n✓ Setup complete. Activate with: source venv/bin/activate"
	@echo "  Then copy .env.sample to .env and add your ANTHROPIC_API_KEY."

# Run a single query (pass QUERY="..." on the command line)
run:
	TOKENIZERS_PARALLELISM=false ./venv/bin/python src/cli/main.py --query_text "$(QUERY)"

# Run the regression test suite
test:
	TOKENIZERS_PARALLELISM=false ./venv/bin/python src/cli/main.py --test_mode

# Rebuild the FAISS index from the Comprehensive Rules
index:
	TOKENIZERS_PARALLELISM=false ./venv/bin/python -c "\
		from src.core.indexers import DatabaseIndexer; \
		DatabaseIndexer(faiss_index_path='./data/indices', data_path='./src/data', raw_docs_path='raw_docs') \
		.create_database_from_large_file()"

# Download the latest Comprehensive Rules
update-rules:
	./venv/bin/python scripts/update_rules.py

# Launch the Streamlit web UI
ui:
	TOKENIZERS_PARALLELISM=false ./venv/bin/streamlit run streamlit_app.py
