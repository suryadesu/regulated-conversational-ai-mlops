# TODO(build): root input variables. Final content also enumerates queue/table/repo/secret names
#   and the eks cluster + default node group + gpu node group settings.
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
