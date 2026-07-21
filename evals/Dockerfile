# Eval harness image: used by the k8s canary-prober Job and runnable ad hoc as
# the CI gate. Root workspace context required for uv resolution.
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app
COPY . .
RUN uv sync --frozen --no-dev --no-editable --package evals

FROM python:3.12-slim
RUN useradd -m nonroot
ENV PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/evals/cases /app/evals/cases
USER nonroot
CMD ["python", "-m", "eval_harness.gate"]
