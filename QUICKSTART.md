# MTG JudgeBot — Quick Start Guide

This guide walks you through running the MTG JudgeBot, an AI-powered Magic: the Gathering rules assistant.

You can run it:
- **Locally** (v1 — direct OpenAI API calls), or
- **With Docker** (v2 — uses an LLM Proxy + Redis caching).

---

## 1. Prerequisites

Make sure you have installed:
- Python 3.10+
- Docker and Docker Compose
- An OpenAI API key
- (Optional) Reddit + Google API keys for external context

---

## 2. Setup

Clone the repository:
```bash
git clone https://github.com/your-repo/mtg-judgebot.git
cd mtg-judgebot
```

Create your `.env` file:
```bash
cp .env.sample .env
```

Edit `.env` to include your keys (OpenAI, Reddit, etc.)

For the proxy version (v2), set:
```bash
USE_LLM_PROXY=true
```

---

## 3. Run Option 1: Full Docker Stack (Recommended for v2)

This launches the complete stack:
- LLM Proxy (FastAPI)
- Redis Cache
- Streamlit Web App

Build and start everything:
```bash
docker compose up --build
```

Once running:
- **Web App**: http://localhost:8501
- **Proxy Health Check**: http://localhost:8080/health

To stop all containers:
```bash
docker compose down
```

---

## 4. Run Option 2: CLI (Local Mode)

If you prefer to run directly on your machine (without Docker):

### (a) Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### (b) Run a single query:
```bash
python src/cli/main.py --query_text "What happens if I have a Blood Moon and an Urborg, Tomb of Yawgmoth?"
```
Or run in test mode to run regression suite:
```bash
python src/cli/main.py --test_mode --start 0 --end 5
```

### (c) Refresh the RAG database (optional):
```bash
python src/cli/main.py --refresh_db
```

---

## 5. Streamlit Web Interface (Local Mode)

Run the web interface manually (no Docker required):
```bash
streamlit run streamlit_app.py
```

Then open: http://localhost:8501

---

## 6. Verify the Proxy (Optional Sanity Check)

If you're running with Docker or the proxy locally, test the health endpoint:
```bash
curl http://localhost:8080/health
```

Expected response:
```json
{"status": "ok"}
```

---

## 7. Summary of Key Commands

| Purpose | Command |
|---------|---------|
| Start full Docker stack | `docker compose up --build` |
| Stop Docker stack | `docker compose down` |
| Run CLI (local mode) | `python src/cli/main.py --query_text "..."` |
| Rebuild FAISS index | `python src/cli/main.py --refresh_db` |
| Run web interface | `streamlit run streamlit_app.py` |
| Check proxy health | `curl http://localhost:8080/health` |