# AWS provider with floci endpoint overrides for local apply: when
# var.aws_endpoints is populated (envs/local.tfvars), every listed service is
# routed to floci; empty (prod) means real AWS endpoints.
terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = var.region
  skip_credentials_validation = var.use_floci
  skip_requesting_account_id  = var.use_floci
  skip_metadata_api_check     = var.use_floci
  access_key                  = var.use_floci ? "test" : null
  secret_key                  = var.use_floci ? "test" : null

  dynamic "endpoints" {
    for_each = length(var.aws_endpoints) > 0 ? [var.aws_endpoints] : []
    content {
      sqs            = lookup(endpoints.value, "sqs", null)
      dynamodb       = lookup(endpoints.value, "dynamodb", null)
      secretsmanager = lookup(endpoints.value, "secretsmanager", null)
      ecr            = lookup(endpoints.value, "ecr", null)
    }
  }
}
