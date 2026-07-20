# TODO(build): AWS provider with floci endpoint overrides for local apply. Final content:
#   - provider "aws" gains a dynamic `endpoints` block populated from var.aws_endpoints when
#     var.use_floci is true (sqs, dynamodb, secretsmanager, ecr all -> http://localhost:4566).
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
}
