# Module wiring. Applied locally against floci: sqs, dynamodb, ecr, secrets.
# Authored + validate/plan-only: iam, eks — gated behind enable_cluster_modules
# (false by default) so a plain apply -var-file=envs/local.tfvars never touches them.
module "sqs" {
  source = "./modules/sqs"
}

module "dynamodb" {
  source = "./modules/dynamodb"
}

module "ecr" {
  source = "./modules/ecr"
  count  = var.enable_ecr ? 1 : 0
}

module "secrets" {
  source = "./modules/secrets"
}

module "iam" {
  source = "./modules/iam"
  count  = var.enable_cluster_modules ? 1 : 0
}

module "eks" {
  source = "./modules/eks"
  count  = var.enable_cluster_modules ? 1 : 0
}
