# Secrets Manager secret holding the managed-provider credential. Name matches
# scripts/seed-aws.sh; in production the External Secrets Operator syncs it to
# a Kubernetes Secret via IRSA (see ../iam).
resource "aws_secretsmanager_secret" "provider_api_key" {
  name        = "gateway/provider-api-key"
  description = "Managed-provider credential for the gateway"
}
