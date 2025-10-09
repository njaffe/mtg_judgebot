proxy/README.md

# JudgeBot LLM Proxy

This directory contains the LLM Proxy Service — a lightweight FastAPI app that routes all JudgeBot LLM requests through a unified endpoint.
It centralizes vendor access, caching, and cost metering, so your main app never calls OpenAI or Anthropic directly.

⸻

## Background

JudgeBot v2 introduces a proxy layer that sits between your app and external LLMs.
It provides:
- A single /v1/chat/completions endpoint for all models/vendors
- Redis caching to avoid duplicate calls
- Basic token, latency, and cost tracking
- Vendor abstraction (e.g., switch from OpenAI to Anthropic with no code change)

When `USE_LLM_PROXY=true`, your app routes through this proxy.

## Structure
proxy/
├── app.py           # FastAPI app (main entrypoint)
├── llm_vendors.py   # Vendor clients (OpenAI, Anthropic)
├── cache.py         # Redis caching layer
├── metering.py      # Cost + token tracking
├── models.py        # Shared request/response schemas
└── requirements.txt # Proxy-only dependencies

## Essentials for Usage

1. Environment Variables

Define these in your project’s .env:
`USE_LLM_PROXY=true`
`PROXY_BASE_URL=http://localhost:8080`

`OPENAI_API_KEY=sk-...`
`ANTHROPIC_API_KEY=...`
`REDIS_URL=redis://localhost:6379/0`

2. Run Locally

From the project root:
`cd proxy`
`pip install -r requirements.txt`
`uvicorn app:app --port 8080 --reload`

Start Redis separately:
`docker run -d -p 6379:6379 redis:7`

3. Test

Health check:
`curl http://localhost:8080/health`

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What happens when a token creature dies?"}]}'
```

4. Integration

The main app (CLI + Streamlit) uses src/external/openai_client.py as a single interface.
That client decides whether to send requests directly to OpenAI or through the proxy, depending on USE_LLM_PROXY.