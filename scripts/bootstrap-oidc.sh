#!/bin/bash
set -euo pipefail

# Bootstrap GitHub Actions OIDC federation and Terraform state bucket.
#
# Prerequisites:
#   - AWS credentials configured locally (aws configure / env vars / SSO)
#   - Terraform >= 1.10 installed
#   - GitHub CLI (`gh`) installed and authenticated

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OIDC_DIR="${SCRIPT_DIR}/../infra/oidc"

source "${SCRIPT_DIR}/utils.sh"
require_commands terraform gh aws

trap 'rm -f "${OIDC_DIR}/oidc.tfplan"' EXIT

init_terraform() {
  info "Initializing Terraform (infra/oidc)"
  cd "${OIDC_DIR}"
  terraform init -input=false
}

plan_and_confirm() {
  info "Planning bootstrap resources"
  terraform plan -input=false -out=oidc.tfplan
  confirm "Apply this plan?"
}

apply() {
  info "Applying bootstrap resources"
  terraform apply -input=false oidc.tfplan
}

set_github_secrets() {
  local role_arn bucket region
  role_arn=$(terraform output -raw github_actions_role_arn)
  bucket=$(terraform output -raw tf_state_bucket)
  region=$(terraform output -raw tf_state_region)

  info "Setting GitHub secrets"
  gh secret set AWS_DEPLOY_ROLE_ARN --body "${role_arn}"
  gh secret set TF_STATE_BUCKET    --body "${bucket}"
  gh secret set TF_STATE_REGION    --body "${region}"
  gh secret set AWS_REGION         --body "${region}"
}

init_terraform
plan_and_confirm
apply
set_github_secrets

success "Bootstrap complete!"
cat <<EOF

Next steps:
  1. Push to main (or workflow_dispatch) to verify the deploy
  2. Clean up old static credentials:
       gh secret delete AWS_ACCESS_KEY_ID
       gh secret delete AWS_SECRET_ACCESS_KEY
     Then deactivate the old IAM access key in the AWS console
EOF
