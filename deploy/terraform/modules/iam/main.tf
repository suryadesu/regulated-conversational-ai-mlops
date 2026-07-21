# IRSA roles (validate/plan-only; never applied against floci): gateway reads
# the provider secret, ticket-worker consumes SQS + writes DynamoDB, and the
# External Secrets Operator syncs Secrets Manager -> Kubernetes Secrets.
locals {
  oidc_condition = {
    StringEquals = {
      "${var.oidc_provider_hostpath}:aud" = "sts.amazonaws.com"
    }
  }
  roles = {
    gateway          = "system:serviceaccount:${var.namespace}:gateway"
    ticket-worker    = "system:serviceaccount:${var.namespace}:ticket-worker"
    external-secrets = "system:serviceaccount:${var.namespace}:external-secrets"
  }
}

resource "aws_iam_role" "irsa" {
  for_each = local.roles
  name     = "${each.key}-irsa"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = var.oidc_provider_arn
        }
        Action    = "sts:AssumeRoleWithWebIdentity"
        Condition = local.oidc_condition
      }
    ]
  })
}

resource "aws_iam_role_policy" "gateway_secrets_read" {
  name = "gateway-secrets-read"
  role = aws_iam_role.irsa["gateway"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = "arn:aws:secretsmanager:*:*:secret:gateway/*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "worker_sqs_dynamo" {
  name = "ticket-worker-sqs-dynamo"
  role = aws_iam_role.irsa["ticket-worker"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl"
        ]
        Resource = "arn:aws:sqs:*:*:escalations*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem"
        ]
        Resource = [
          "arn:aws:dynamodb:*:*:table/idempotency",
          "arn:aws:dynamodb:*:*:table/tickets"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "eso_secrets_read" {
  name = "external-secrets-read"
  role = aws_iam_role.irsa["external-secrets"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret",
          "secretsmanager:ListSecrets"
        ]
        Resource = "*"
      }
    ]
  })
}
