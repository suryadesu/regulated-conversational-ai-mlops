# Production variable values (real AWS, no endpoint overrides). iam/eks are
# instantiated here but only ever validate/plan in CI — never auto-applied.
region                 = "us-east-1"
use_floci              = false
aws_endpoints          = {}
enable_cluster_modules = true
