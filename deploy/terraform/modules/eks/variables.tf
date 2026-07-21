variable "cluster_name" {
  description = "EKS cluster name."
  type        = string
  default     = "regulated-conv-ai"
}

variable "kubernetes_version" {
  description = "EKS control-plane version."
  type        = string
  default     = "1.29"
}

variable "cluster_role_arn" {
  description = "IAM role assumed by the EKS control plane."
  type        = string
  default     = "arn:aws:iam::000000000000:role/eks-cluster-example"
}

variable "node_role_arn" {
  description = "IAM role assumed by worker nodes."
  type        = string
  default     = "arn:aws:iam::000000000000:role/eks-node-example"
}

variable "subnet_ids" {
  description = "Subnets for the control plane and node groups (multi-AZ)."
  type        = list(string)
  default     = ["subnet-00000000000000000", "subnet-11111111111111111"]
}

variable "default_node_instance_types" {
  description = "Instance types for the default (CPU) node group."
  type        = list(string)
  default     = ["m6i.large"]
}

variable "gpu_node_instance_types" {
  description = "Instance types for the GPU node group."
  type        = list(string)
  default     = ["g5.xlarge"]
}
