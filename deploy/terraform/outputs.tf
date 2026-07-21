# Root outputs: queue URLs, table names, repo URLs, secret ARN; IRSA/EKS
# outputs only exist when enable_cluster_modules = true.
output "main_queue_url" {
  value = module.sqs.main_queue_url
}

output "dlq_url" {
  value = module.sqs.dlq_url
}

output "idempotency_table_name" {
  value = module.dynamodb.idempotency_table_name
}

output "tickets_table_name" {
  value = module.dynamodb.tickets_table_name
}

output "repository_urls" {
  value = try(module.ecr[0].repository_urls, {})
}

output "provider_secret_arn" {
  value = module.secrets.secret_arn
}

output "irsa_role_arns" {
  value = try(module.iam[0].role_arns, {})
}

output "eks_cluster_endpoint" {
  value = try(module.eks[0].cluster_endpoint, null)
}
