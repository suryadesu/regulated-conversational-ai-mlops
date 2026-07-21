output "cluster_endpoint" {
  value = aws_eks_cluster.this.endpoint
}

output "cluster_name" {
  value = aws_eks_cluster.this.name
}

output "node_group_arns" {
  value = {
    default = aws_eks_node_group.default.arn
    gpu     = aws_eks_node_group.gpu.arn
  }
}
