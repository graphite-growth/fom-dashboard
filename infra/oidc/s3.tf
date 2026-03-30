
locals {
  create_bucket = var.tf_state_bucket == ""
  bucket_name   = local.create_bucket ? aws_s3_bucket._[0].id : var.tf_state_bucket
  bucket_arn    = local.create_bucket ? aws_s3_bucket._[0].arn : "arn:aws:s3:::${var.tf_state_bucket}"
}

resource "aws_s3_bucket" "_" {
  count  = local.create_bucket ? 1 : 0
  bucket = "${var.project_name}-tf-state"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "_" {
  count  = local.create_bucket ? 1 : 0
  bucket = aws_s3_bucket._[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "_" {
  count  = local.create_bucket ? 1 : 0
  bucket = aws_s3_bucket._[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

