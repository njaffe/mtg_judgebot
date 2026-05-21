# MTG JudgeBot

An AI-powered rules judge for Magic: The Gathering. Ask complex rules questions and get accurate, citation-backed rulings grounded in the official Comprehensive Rules.

## How It Works

```
User Question
    │
    ▼
┌─────────────────────────────────────────┐
│  1. Card Lookup (Scryfall API)          │  ← Oracle text + official rulings
│  2. Rules Retrieval (FAISS + embeddings)│  ← Top 10 relevant CR sections
│  3. RAG Answer (Claude Sonnet 4.6)      │  ← Grounded in retrieved rules
│  4. Synthesis (Claude Sonnet 4.6)       │  ← Final ruling with citations
└─────────────────────────────────────────┘
    │
    ▼
  Answer with rule citations + step-by-step reasoning
```

**Key design decisions:**
- **Embeddings are local** — uses `all-MiniLM-L6-v2` via sentence-transformers. No OpenAI key needed.
- **Rule-aware chunking** — the CR is parsed by rule number (e.g., 702.16a), not by character count. Subrules stay grouped with their parents.
- **Anti-hallucination prompting** — the LLM is instructed to only cite rules that appear verbatim in the retrieved context.
- **Card data from Scryfall** — Oracle text and official rulings are fetched live, so the bot understands what specific cards do.
- **External sources optional** — Google and Reddit search are available but off by default to keep answers authoritative.

## Quick Start

```bash
# 1. Clone and enter the project
git clone https://github.com/your-repo/mtg-judgebot.git
cd mtg-judgebot

# 2. Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure API key
cp .env.sample .env
# Edit .env and add your Anthropic API key (https://console.anthropic.com)

# 4. Build the FAISS index (one-time, takes ~10 seconds)
make index

# 5. Ask a question
make run QUERY="Does deathtouch work with trample?"
```

Or use the web UI:
```bash
make ui
# Opens at http://localhost:8501
```

## Project Structure

```
mtg_judgebot/
├── src/
│   ├── core/
│   │   ├── indexers.py             # Rule-aware CR parser + FAISS indexing
│   │   ├── rag_service.py          # Embed query → FAISS search → Claude answer
│   │   └── synthesis_service.py    # Combine RAG + card data → final ruling
│   ├── external/
│   │   ├── anthropic_client.py     # Claude API wrapper
│   │   ├── scryfall_client.py      # Card lookup (Oracle text + rulings)
│   │   ├── google_client.py        # Google Custom Search (optional)
│   │   └── reddit_client.py        # Reddit search via PRAW (optional)
│   ├── cli/
│   │   └── main.py                 # CLI entry point + query orchestration
│   └── data/
│       ├── raw_docs/
│       │   └── mtg_rules.txt       # Comprehensive Rules (Feb 2025)
│       └── tests/
│           ├── regression_suite.json
│           └── test_results_*.json
├── data/
│   └── indices/                    # FAISS index + document store
├── scripts/
│   └── update_rules.py             # Download latest CR from Wizards
├── streamlit_app.py                # Streamlit web UI
├── makefile                        # Common commands (setup, run, test, etc.)
├── requirements.txt                # Python dependencies
├── .env.sample                     # Environment variable template
└── .env                            # Your local config (gitignored)
```

## Usage

### CLI

```bash
# Single question
python src/cli/main.py --query_text "Can I equip Swiftfoot Boots in response to a kill spell?"

# With external sources enabled
python src/cli/main.py --query_text "Your question" --enable_external

# Regression test suite
python src/cli/main.py --test_mode

# Subset of tests
python src/cli/main.py --test_mode --start 0 --end 3
```

### Web UI

```bash
streamlit run streamlit_app.py
```

Features: question input, source breakdown (RAG, card data, external), usage stats, external sources toggle.

### Makefile Shortcuts

| Command | Description |
|---------|-------------|
| `make setup` | Create venv and install dependencies |
| `make run QUERY="..."` | Run a single query |
| `make test` | Run the regression test suite |
| `make index` | Rebuild the FAISS index |
| `make update-rules` | Download the latest Comprehensive Rules |
| `make ui` | Launch the Streamlit web UI |

## Configuration

All configuration is in `.env`. Copy `.env.sample` to get started.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | **Yes** | — | Claude API key for chat/synthesis |
| `ENABLE_EXTERNAL_SOURCES` | No | `false` | Enable Google/Reddit supplementary search |
| `FAISS_INDEX_PATH` | No | `./data/indices` | Where the FAISS index is stored |
| `DATA_PATH` | No | `./src/data` | Where raw documents live |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Sentence-transformers model name |
| `GOOGLE_API_KEY` | No | — | Google Custom Search key (if external enabled) |
| `GOOGLE_CSE_ID` | No | — | Google Custom Search engine ID |
| `REDDIT_CLIENT_ID` | No | — | Reddit API client ID (if external enabled) |
| `REDDIT_CLIENT_SECRET` | No | — | Reddit API client secret |

## Updating the Rules

The Comprehensive Rules are updated with each MTG set release. To update:

```bash
python scripts/update_rules.py   # Downloads latest CR
make index                        # Rebuild the FAISS index
```

## Cost

Each query costs approximately **$0.007–$0.02** depending on question complexity (Claude Sonnet 4.6 at $3/M input, $15/M output tokens). Embeddings are free (local model).

## License

MIT
