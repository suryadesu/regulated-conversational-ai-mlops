#!/usr/bin/env bash
# Drain-invariant smoke test: open an SSE stream against the gateway, trigger a
# rolling restart mid-stream, and assert the open stream completes ([DONE])
# instead of being cut short.
set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
OUT="$(mktemp)"

curl -sN "$GATEWAY_URL/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"long streaming request for the drain smoke test"}],"stream":true}' \
  > "$OUT" &
STREAM_PID=$!

sleep 1
kubectl argo rollouts restart gateway -n default 2>/dev/null \
  || kubectl rollout restart deployment/gateway -n default 2>/dev/null \
  || echo "no rollout to restart (compose mode): asserting stream completion only"

wait "$STREAM_PID"

if grep -q '\[DONE\]' "$OUT"; then
  echo "PASS: stream completed"
else
  echo "FAIL: stream cut short"
  cat "$OUT"
  exit 1
fi
