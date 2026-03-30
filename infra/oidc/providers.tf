terraform {
  required_version = ">= 1.10"

  # Local backend — this is the bootstrap module, so no S3 bucket exists yet.
  # State is stored at infra/oidc/terraform.tfstate (gitignored).
  backend "local" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}
