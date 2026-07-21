# Idempotency table (pk hash key + expires_at TTL) and tickets table (id hash
# key). The idempotency schema MUST match
# services/ticket-worker/src/ticket_worker/idempotency.py and scripts/seed-aws.sh.
resource "aws_dynamodb_table" "idempotency" {
  name         = "idempotency"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  attribute {
    name = "pk"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "tickets" {
  name         = "tickets"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}
