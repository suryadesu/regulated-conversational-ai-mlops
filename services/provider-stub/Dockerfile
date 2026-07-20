# Multi-stage uv build; root workspace context required so uv can resolve the
# whole workspace (pyproject.toml + uv.lock + member manifests).
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app
COPY . .
RUN uv sync --frozen --no-dev --no-editable --package provider-stub

FROM python:3.12-slim
RUN useradd -m nonroot
ENV PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH" PROVIDER_STUB_CANNED_DIR=/app/canned
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/services/provider-stub/canned /app/canned
USER nonroot
EXPOSE 8080
CMD ["uvicorn", "provider_stub.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
