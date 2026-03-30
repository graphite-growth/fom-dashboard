#!/bin/bash
set -euo pipefail

# Set GitHub Actions secrets and variables for the deploy workflow.
#
# Secrets managed by bootstrap-oidc.sh are not included here
# (AWS_DEPLOY_ROLE_ARN, TF_STATE_BUCKET).
#
# Prerequisites:
#   - GitHub CLI (`gh`) installed and authenticated

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

source "${SCRIPT_DIR}/utils.sh"
require_commands gh

set_secrets() {
  info "Secrets (sensitive)"
  prompt_gh secret GOOGLE_CLIENT_ID     "Google OAuth client ID"
  prompt_gh secret GOOGLE_CLIENT_SECRET "Google OAuth client secret"
}

set_variables() {
  info "Variables (non-sensitive)"
  prompt_gh variable VPC_ID            "VPC ID"
  prompt_gh variable APP_SUBNET_IDS    "App subnet IDs (JSON array)"
  prompt_gh variable ELB_SUBNET_IDS    "ELB subnet IDs (JSON array)"
  prompt_gh variable SECURITY_GROUP_ID "Security group ID"
  prompt_gh variable HOSTED_ZONE_ID    "Route 53 hosted zone ID"
  prompt_gh variable CERTIFICATE_ARN   "ACM certificate ARN"
}

echo "Set GitHub Actions secrets and variables for the deploy workflow."
echo "Press Enter to skip any value you don't want to change."
echo ""

set_secrets
set_variables

success "All values configured!"
