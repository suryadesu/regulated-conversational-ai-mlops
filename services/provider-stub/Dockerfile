# TODO(build): image for the deterministic provider stub. Enumerated final content:
#   - FROM python:3.12-slim; install uv; `uv sync --frozen --package provider-stub`; nonroot USER.
#   - EXPOSE 8080.
#   - CMD ["uvicorn", "provider_stub.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"].
FROM python:3.12-slim
WORKDIR /app
CMD ["echo", "TODO(build): provider-stub image not implemented"]
