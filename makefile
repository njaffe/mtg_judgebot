.PHONY: up down logs rebuild cli proxy-health fmt

up:
\tdocker compose up --build

down:
\tdocker compose down

logs:
\tdocker compose logs -f

rebuild:
\tdocker compose build --no-cache

cli:
\tdocker compose exec app python src/cli/main.py --query_text "How does Blood Moon interact with Urborg?"

proxy-health:
\tcurl -s http://localhost:8080/health || true