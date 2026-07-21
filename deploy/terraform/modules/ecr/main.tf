# One ECR repository per service image, immutable tags (promotion always
# references the sha tag; `latest` is never deployed), plus an untagged-expiry
# lifecycle policy.
resource "aws_ecr_repository" "repos" {
  for_each             = toset(["gateway", "provider-stub", "ticket-worker", "evals"])
  name                 = each.key
  image_tag_mutability = "IMMUTABLE"
}

resource "aws_ecr_lifecycle_policy" "repos" {
  for_each   = aws_ecr_repository.repos
  repository = each.value.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "expire untagged images after 14 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 14
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
