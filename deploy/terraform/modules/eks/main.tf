# EKS cluster + default node group + GPU node group (validate/plan-only; kind
# is the local cluster). The GPU group carries the nvidia.com/gpu taint the
# prod overlay tolerates; the NVIDIA device plugin addon publishes the
# extended resource.
resource "aws_eks_cluster" "this" {
  name     = var.cluster_name
  role_arn = var.cluster_role_arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids = var.subnet_ids
  }
}

resource "aws_eks_node_group" "default" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.cluster_name}-default"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.subnet_ids
  instance_types  = var.default_node_instance_types

  scaling_config {
    desired_size = 2
    min_size     = 1
    max_size     = 5
  }
}

resource "aws_eks_node_group" "gpu" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.cluster_name}-gpu"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.subnet_ids
  instance_types  = var.gpu_node_instance_types
  ami_type        = "AL2_x86_64_GPU"

  labels = {
    "node-pool" = "gpu"
  }

  taint {
    key    = "nvidia.com/gpu"
    value  = "present"
    effect = "NO_SCHEDULE"
  }

  scaling_config {
    desired_size = 1
    min_size     = 0
    max_size     = 4
  }
}
