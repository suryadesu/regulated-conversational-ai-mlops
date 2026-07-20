# TODO(build): image for the SQS ticket worker. Enumerated final content:
#   - FROM python:3.12-slim; install uv; `uv sync --frozen --package ticket-worker`; nonroot USER.
#   - No exposed port (queue consumer).
#   - CMD ["python", "-m", "ticket_worker.main"].
FROM python:3.12-slim
WORKDIR /app
CMD ["echo", "TODO(build): ticket-worker image not implemented"]
