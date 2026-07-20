# Multi-stage uv build; root workspace context required so uv can resolve the
# whole workspace (ticket-worker depends on the gateway member package).
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app
COPY . .
RUN uv sync --frozen --no-dev --no-editable --package ticket-worker

FROM python:3.12-slim
RUN useradd -m nonroot
ENV PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
# The worker loads the same versioned prompt store as the gateway.
COPY --from=builder /app/prompts /app/prompts
USER nonroot
CMD ["python", "-m", "ticket_worker.main"]
