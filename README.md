# Magic: The Gathering AI Judge

An AI-powered tool designed to assist with complex rules scenarios and edge cases in Magic: The Gathering.

## Table of Contents

- Overview
- Features
- Installation
- Usage
- Project Structure
- Future Improvements
- Contributing
- License

## Overview

This project implements a Retrieval-Augmented Generation (RAG) system to create an AI “judge” for Magic: The Gathering (MTG). The tool helps players and enthusiasts navigate the complex rules and edge cases that often arise in the game. By leveraging large language models (LLMs) and a comprehensive rules database, this AI judge provides quick and accurate answers to MTG-related queries.

The system uses agents within the RAG framework to query various sources, including a custom database of MTG rules, as well as external platforms like Reddit and Google, to gather relevant context and insights. The AI then generates a combined answer, ensuring players have access to both authoritative rules information and community perspectives.

## Features

- RAG-based query system: Utilizes the entire MTG rules corpus (approximately 148,000 words).
- Integration with external sources: Queries Reddit and Google for additional context and community insights.
- Multi-source answer compilation: Combines results from the rules corpus, Reddit, and Google searches for more robust answers.
- Agent-based architecture: Uses agents as part of the RAG framework to optimize information retrieval and answer generation.
- Natural language processing: Understands and responds to MTG-specific queries in natural language, providing intuitive answers.

## Installation

### Prerequisites

- Python 3.7+
- Environment variables configured (see .env file for API keys)

### Steps

1. Clone the repository:

	```sh
	git clone https://github.com/your-repo/mtg-ai-judge.git
	cd mtg-ai-judge
	```

2. Create and activate a virtual environment:

	```sh
	python3 -m venv venv
	source venv/bin/activate
	```

3. Install the required packages:

	```sh
	pip install -r requirements.txt
	```

4. Set up your environment variables in a `.env` file (refer to the `.env.sample` file in the repo):

	```env
	OPENAI_API_KEY=your_openai_api_key
	GOOGLE_CSE_ID=your_google_cse_id
	GOOGLE_API_KEY=your_google_api_key
	REDDIT_CLIENT_ID=your_reddit_client_id
	REDDIT_CLIENT_SECRET=your_reddit_client_secret
	REDDIT_USER_AGENT=your_reddit_user_agent
	```

## Usage

### Quick Start

1. **Activate your virtual environment:**
   ```sh
   source venv/bin/activate
   ```

2. **Ask a question:**
   ```sh
   python src/cli/main.py --query_text "What happens when a creature dies?"
   ```

3. **That's it!** The AI Judge will query multiple sources and give you a comprehensive answer.

### Command Line Usage

#### Basic Query
```bash
# Ask a simple question
python src/cli/main.py --query_text "What happens when a creature dies?"

# Ask a complex rules question
python src/cli/main.py --query_text "If I have a creature with an equipment on it, and an opponent gains control of the creature, what happens?"
```

#### Advanced Options
```bash
# Run test suite
python src/cli/main.py --test_mode --start 0 --end 5

# Refresh the RAG database
python src/cli/main.py --refresh_db

# Customize Reddit search
python src/cli/main.py --query_text "Your question" --subreddit "mtgrules" --limit 20
```

#### All Available Options
```bash
python src/cli/main.py --help
```

### Programmatic Usage

#### Using the CLI Programmatically
```python
from src.cli.main import MTGJudgeCLI

# Initialize the CLI
cli = MTGJudgeCLI()

# Ask a single question
result = cli.run_single_query("What happens when a creature dies?")
print(result['final_answer'])

# Run test suite programmatically
results = cli.run_test_suite(start=0, end=5)
for result in results:
    print(f"Q: {result['query']}")
    print(f"A: {result['response']}\n")
```

#### Using Individual Services
```python
from src.core.synthesis_service import SynthesisService
from src.core.rag_service import RAGService
from src.external.google_client import GoogleClient
from src.external.reddit_client import RedditClient

# Initialize services
synthesis = SynthesisService()
rag = RAGService()
google = GoogleClient()
reddit = RedditClient()

# Query individual sources
rag_response = rag.query("Your question here")
google_response = google.search("Your question here")
reddit_response = reddit.search("Your question here")

# Synthesize the final answer
final_answer = synthesis.synthesize_response(
    rag_response, google_response, reddit_response, "Your question here"
)
print(final_answer)
```

### Web Interface

You can also use the Streamlit web interface:

```bash
streamlit run streamlit_app.py
```

This provides a user-friendly web interface for asking questions.


## Project Structure

The project follows a clean, service-based architecture with clear separation of concerns:

```
mtg_judgebot/
├── src/                          # Source code
│   ├── core/                    # Core business logic
│   │   ├── synthesis_service.py # Answer synthesis
│   │   ├── rag_service.py       # RAG database operations
│   │   └── indexers.py         # Database indexing
│   ├── external/                # External API integrations
│   │   ├── google_client.py    # Google Search API
│   │   ├── reddit_client.py    # Reddit API
│   │   └── openai_client.py    # OpenAI API
│   ├── cli/                     # Command-line interface
│   │   └── main.py             # CLI entry point
│   └── utils/                   # Utility functions
├── data/                        # Data storage
│   ├── raw_docs/               # Raw documents
│   ├── indices/                # FAISS indices
│   └── tests/                   # Test data
├── streamlit_app.py            # Web interface
├── requirements.txt            # Dependencies
└── .env                       # Configuration
```

## Contributing

Contributions are welcome! Please fork the repository, create a new branch, and submit a pull request.

## License

This project is licensed under the MIT License.
