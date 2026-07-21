# Root input variables. Resource names (queues, tables, repos, secret) are
# fixed literals inside their modules — no caller ever passes alternatives.
variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "use_floci" {
  description = "Target floci locally: skip credential/metadata validation and use endpoint overrides."
  type        = bool
  default     = false
}

variable "aws_endpoints" {
  description = "Per-service endpoint overrides for floci (empty in production)."
  type        = map(string)
  default     = {}
}

variable "enable_cluster_modules" {
  description = "Instantiate the validate/plan-only iam and eks modules (true in prod)."
  type        = bool
  default     = false
}

variable "enable_ecr" {
  description = "Create ECR repositories (true in prod/CI-with-Docker; false against socketless floci)."
  type        = bool
  default     = true
}
