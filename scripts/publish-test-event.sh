#!/usr/bin/env bash
# Publish a sample escalation event to the SQS main queue (floci), exercising
# the ticket-worker end to end. Event shape matches ticket_worker.ticket.draft_ticket.
set -euo pipefail

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
ENDPOINT="${FLOCI_ENDPOINT:-http://localhost:4566}"

QUEUE_URL=$(aws --endpoint-url "$ENDPOINT" sqs get-queue-url \
  --queue-name escalations --query QueueUrl --output text)
EVENT_ID=$(uuidgen 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())' 2>/dev/null \
  || python -c 'import uuid; print(uuid.uuid4())' 2>/dev/null \
  || echo "evt-$(date +%s)-$RANDOM")

aws --endpoint-url "$ENDPOINT" sqs send-message \
  --queue-url "$QUEUE_URL" \
  --message-body "{\"event_id\": \"$EVENT_ID\", \"summary\": \"Test escalation\", \"customer_id\": \"test-customer\"}" >/dev/null

echo "published event_id=$EVENT_ID to $QUEUE_URL"
