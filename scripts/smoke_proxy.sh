#!/usr/bin/env bash
set -euo pipefail
curl -s http://localhost:8080/health | grep -q '"ok"' && echo "Proxy healthy"
curl -s -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Say hello in one sentence."}]}' \
  | grep -q '"choices"' && echo "Proxy responded"