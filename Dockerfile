# Multi-stage build: proxy (FastAPI) + app (Streamlit/CLI)

# ---------- Base ----------
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# System deps (faiss wheels often need libgomp1)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

# ---------- Proxy image ----------
FROM base AS proxy
# Install proxy-only deps
COPY proxy/requirements.txt /app/proxy/requirements.txt
RUN pip install --no-cache-dir -r /app/proxy/requirements.txt
# Add proxy source
COPY proxy /app/proxy
WORKDIR /app/proxy
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]

# ---------- App image (Streamlit/CLI) ----------
FROM base AS app
# Install app deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
# Add entire repo so src/*, streamlit_app.py, etc. are available
COPY . /app
WORKDIR /app
EXPOSE 8501
# Default to Streamlit; override in compose/CLI as needed
CMD ["streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]