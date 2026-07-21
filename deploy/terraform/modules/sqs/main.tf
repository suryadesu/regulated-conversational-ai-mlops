# SQS main queue + DLQ with redrive (maxReceiveCount=3). Names/values are fixed
# literals: no caller passes alternatives, and scripts/seed-aws.sh describes the
# identical resources for the CLI-seeded path.
resource "aws_sqs_queue" "dlq" {
  name = "escalations-dlq"
}

resource "aws_sqs_queue" "main" {
  name                       = "escalations"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}
