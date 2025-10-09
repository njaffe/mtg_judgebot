# Magic: The Gathering AI Judge

An AI-powered tool designed to assist with complex rules scenarios and edge cases in Magic: The Gathering.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Versions](#versions)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This project implements a Retrieval-Augmented Generation (RAG) system to create an AI “judge” for Magic: The Gathering (MTG).  
The tool helps players and enthusiasts navigate the complex rules and edge cases that often arise in the game.  
By leveraging large language models (LLMs) and a comprehensive rules database, this AI judge provides quick and accurate answers to MTG-related queries.

The system uses agents within the RAG framework to query various sources — including a custom rules database, Reddit, and Google — to gather relevant context and insights.  
It then synthesizes a final answer using LLMs, providing both **authoritative rules references** and **community perspectives**.

---

## Features

- **RAG-based query system** — Utilizes the full MTG rules corpus (~148K words).  
- **External source integration** — Queries Reddit and Google for supplemental context.  
- **Multi-source synthesis** — Combines RAG, Reddit, and Google responses into a single answer.  
- **Agent-based architecture** — Modular, service-oriented design for easy extension.  
- **LLM Proxy (v2)** — Adds caching, cost metering, and vendor routing for scalable usage.  
- **Web and CLI interfaces** — Use via Streamlit UI or command line.  

---

## Installation

### Prerequisites

- Python 3.9+  
- Environment variables configured (`.env` for API keys)  
- [Docker](https://www.docker.com/) (optional, for running the proxy + Redis)

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-repo/mtg-ai-judge.git
   cd mtg-ai-judge
   ```


2.	**Create and activate a virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate
```

3.	**Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
   
   Copy `.env.sample` → `.env` and fill in:
   
   ```bash
   # Required API keys
   OPENAI_API_KEY=your_openai_api_key
   GOOGLE_CSE_ID=your_google_cse_id
   GOOGLE_API_KEY=your_google_api_key
   REDDIT_CLIENT_ID=your_reddit_client_id
   REDDIT_CLIENT_SECRET=your_reddit_client_secret
   REDDIT_USER_AGENT=your_reddit_user_agent
   
   # Optional (v2 proxy)
   USE_LLM_PROXY=true
   PROXY_BASE_URL=http://localhost:8080
   REDIS_URL=redis://localhost:6379/0
   ```

---

## Usage

### Option 1: Command Line

```bash
# Basic query
python src/cli/main.py --query_text "What happens when a creature dies?"

# Refresh RAG database
python src/cli/main.py --refresh_db

# Run test suite
python src/cli/main.py --test_mode --start 0 --end 5
```

### Option 2: Web Interface

```bash
streamlit run streamlit_app.py
```

Access at http://localhost:8501

### Option 3: Docker (Recommended for v2)

Run the full system (app + proxy + Redis):

```bash
docker compose up --build
```

- **App**: http://localhost:8501
- **Proxy**: http://localhost:8080

---

## Project Structure

```
mtg_judgebot/
├── src/
│   ├── core/                    # Core logic (RAG + synthesis)
│   │   ├── synthesis_service.py
│   │   ├── rag_service.py
│   │   └── indexers.py
│   ├── external/                # External APIs + proxy adapter
│   │   ├── google_client.py
│   │   ├── reddit_client.py
│   │   └── openai_client.py     # Routes through proxy if enabled
│   ├── cli/
│   │   └── main.py              # CLI entrypoint
│   └── utils/
├── proxy/                       # New in v2: LLM proxy service
│   ├── app.py                   # FastAPI app
│   ├── llm_vendors.py           # Vendor routing (OpenAI/Anthropic)
│   ├── cache.py                 # Redis caching
│   ├── metering.py              # Token + cost tracking
│   ├── models.py                # API schemas
│   └── requirements.txt
├── data/
│   ├── raw_docs/
│   ├── indices/
│   └── tests/
├── streamlit_app.py             # Web interface
├── requirements.txt
└── .env
```

---

## Versions

- **v1.0.0** — Original release
  - Local-only; direct OpenAI calls
- **v2.0.0** — Adds LLM Proxy + Docker Support
  - FastAPI proxy service for model routing
  - Redis caching and cost metering
  - Configurable vendor abstraction via .env
  - Run with `docker compose up`

---

## Contributing

[Contributing guidelines would go here]

---

## License

This project is licensed under the MIT License.