
resource "aws_ssm_parameter" "google_client_id" {
  name  = "${var.ssm_prefix}/GOOGLE_CLIENT_ID"
  type  = "SecureString"
  value = var.google_client_id
}

resource "aws_ssm_parameter" "google_client_secret" {
  name  = "${var.ssm_prefix}/GOOGLE_CLIENT_SECRET"
  type  = "SecureString"
  value = var.google_client_secret
}

resource "aws_ssm_parameter" "auth_secret" {
  name  = "${var.ssm_prefix}/AUTH_SECRET"
  type  = "SecureString"
  value = random_bytes.auth_secret.base64
}


