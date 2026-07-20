# TODO(build): local (floci) variable values.
region    = "us-east-1"
use_floci = true
aws_endpoints = {
  sqs            = "http://localhost:4566"
  dynamodb       = "http://localhost:4566"
  secretsmanager = "http://localhost:4566"
  ecr            = "http://localhost:4566"
}
