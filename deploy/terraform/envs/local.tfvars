# Local (floci) variable values. enable_ecr=false: floci's ECR emulation spawns
# a real registry:2 container via the Docker engine, which floci-inside-compose
# cannot reach (no Docker socket) — repo creation hangs. Locally, images are
# kind-loaded / GHCR anyway; the ecr module stays validate/plan-only here.
region    = "us-east-1"
use_floci = true
aws_endpoints = {
  sqs            = "http://localhost:4566"
  dynamodb       = "http://localhost:4566"
  secretsmanager = "http://localhost:4566"
  ecr            = "http://localhost:4566"
}
enable_ecr = false
