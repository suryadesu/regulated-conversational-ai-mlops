# TODO(build): module wiring. Applied locally against floci: sqs, dynamodb, ecr, secrets.
#   Authored + validate/plan-only: iam, eks. Each module is instantiated with its inputs here.
module "sqs" {
  source = "./modules/sqs"
}

module "dynamodb" {
  source = "./modules/dynamodb"
}

module "ecr" {
  source = "./modules/ecr"
}

module "secrets" {
  source = "./modules/secrets"
}

module "iam" {
  source = "./modules/iam"
}

module "eks" {
  source = "./modules/eks"
}
