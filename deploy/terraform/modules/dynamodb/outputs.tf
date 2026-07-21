output "idempotency_table_name" {
  value = aws_dynamodb_table.idempotency.name
}

output "tickets_table_name" {
  value = aws_dynamodb_table.tickets.name
}

output "table_arns" {
  value = {
    idempotency = aws_dynamodb_table.idempotency.arn
    tickets     = aws_dynamodb_table.tickets.arn
  }
}
