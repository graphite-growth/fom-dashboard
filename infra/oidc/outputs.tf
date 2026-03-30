output "github_actions_role_arn" {
  description = "IAM role ARN for GitHub Actions OIDC deploy — add as AWS_DEPLOY_ROLE_ARN secret"
  value       = aws_iam_role._.arn
}

output "tf_state_bucket" {
  description = "S3 bucket name for Terraform state — add as TF_STATE_BUCKET secret"
  value       = local.bucket_name
}

output "tf_state_region" {
  description = "AWS region for Terraform state — add as TF_STATE_REGION secret"
  value       = var.region
}
