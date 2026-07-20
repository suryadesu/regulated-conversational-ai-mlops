# Multi-stage uv build; root workspace context required so uv can resolve the
# whole workspace (pyproject.toml + uv.lock + member manifests).
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app
COPY . .
RUN uv sync --frozen --no-dev --no-editable --package gateway

FROM python:3.12-slim
RUN useradd -m nonroot
ENV PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
# Runtime data read via repo-relative Settings defaults (prompt_dir, price_table_path).
COPY --from=builder /app/prompts /app/prompts
COPY --from=builder /app/services/gateway/config /app/services/gateway/config
USER nonroot
EXPOSE 8000
CMD ["uvicorn", "gateway.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "170"]
