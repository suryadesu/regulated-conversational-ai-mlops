output "role_arns" {
  value = { for name, role in aws_iam_role.irsa : name => role.arn }
}
