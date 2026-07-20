#!/usr/bin/env bash
# Seed floci with the platform's AWS resources: SQS main queue + DLQ with
# redrive (maxReceiveCount=3), DynamoDB idempotency + tickets tables, and the
# managed-provider credential in Secrets Manager.
# Schemas MUST match services/ticket-worker/src/ticket_worker/idempotency.py
# and deploy/terraform/modules/{sqs,dynamodb,secrets}.
set -euo pipefail

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
ENDPOINT="${FLOCI_ENDPOINT:-http://localhost:4566}"
awslocal() { aws --endpoint-url "$ENDPOINT" "$@"; }

echo "waiting for floci at $ENDPOINT ..."
for _ in $(seq 1 30); do
  if curl -sf "$ENDPOINT" >/dev/null 2>&1 || curl -sf "$ENDPOINT/_localstack/health" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "creating DLQ ..."
DLQ_URL=$(awslocal sqs create-queue --queue-name escalations-dlq --query QueueUrl --output text)
DLQ_ARN=$(awslocal sqs get-queue-attributes --queue-url "$DLQ_URL" \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

echo "creating main queue with redrive (maxReceiveCount=3) ..."
QUEUE_URL=$(awslocal sqs create-queue --queue-name escalations \
  --attributes "{\"VisibilityTimeout\":\"60\",\"RedrivePolicy\":\"{\\\"deadLetterTargetArn\\\":\\\"$DLQ_ARN\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\"}" \
  --query QueueUrl --output text)

echo "creating DynamoDB tables ..."
awslocal dynamodb create-table --table-name idempotency \
  --attribute-definitions AttributeName=pk,AttributeType=S \
  --key-schema AttributeName=pk,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST >/dev/null
awslocal dynamodb update-time-to-live --table-name idempotency \
  --time-to-live-specification "Enabled=true,AttributeName=expires_at" >/dev/null
awslocal dynamodb create-table --table-name tickets \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST >/dev/null

echo "creating Secrets Manager secret ..."
awslocal secretsmanager create-secret --name gateway/provider-api-key \
  --secret-string "test-dummy-key" >/dev/null

echo "seeded OK"
echo "queue_url=$QUEUE_URL"
