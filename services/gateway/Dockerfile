# TODO(build): multi-stage uv build, nonroot runtime. Enumerated final content:
#   - builder stage (python:3.12-slim): install uv; COPY workspace; `uv sync --frozen --package gateway`.
#   - runtime stage (python:3.12-slim): COPY .venv + src; create/USER nonroot; PYTHONUNBUFFERED=1.
#   - EXPOSE 8000.
#   - CMD ["uvicorn", "gateway.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"].
FROM python:3.12-slim
WORKDIR /app
CMD ["echo", "TODO(build): gateway image not implemented"]
