variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "fom-dashboard"
}

variable "github_repo" {
  description = "GitHub repository in owner/name format for OIDC trust"
  type        = string
}

variable "tf_state_bucket" {
  description = "Existing S3 bucket name for Terraform state. Leave empty to create one."
  type        = string
  default     = ""
}
