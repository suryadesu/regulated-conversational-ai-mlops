variable "oidc_provider_arn" {
  description = "ARN of the cluster's IAM OIDC provider (from the eks module in a real apply)."
  type        = string
  default     = "arn:aws:iam::000000000000:oidc-provider/example"
}

variable "oidc_provider_hostpath" {
  description = "OIDC provider host/path used in trust-policy conditions."
  type        = string
  default     = "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLE"
}

variable "namespace" {
  description = "Kubernetes namespace of the service accounts."
  type        = string
  default     = "default"
}
