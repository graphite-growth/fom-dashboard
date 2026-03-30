#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
INFRA_DIR="${PROJECT_DIR}/infra/app"

source "${SCRIPT_DIR}/utils.sh"
require_commands zip aws terraform git

APP_NAME="fom-dashboard"
BUCKET="${TF_STATE_BUCKET:?TF_STATE_BUCKET is required}"
REGION="${TF_STATE_REGION:?TF_STATE_REGION is required}"
SHORT_SHA=$(git -C "${PROJECT_DIR}" rev-parse --short HEAD 2>/dev/null || echo "local")
VERSION_LABEL="${APP_NAME}-$(date +%Y%m%d%H%M%S)-${SHORT_SHA}"
ZIP_FILE="/tmp/${VERSION_LABEL}.zip"

trap 'rm -f "${ZIP_FILE}"' EXIT

package() {
  info "Packaging application as ${VERSION_LABEL}"
  cd "${PROJECT_DIR}"
  zip -r "${ZIP_FILE}" \
      docker-compose.yml \
      backend/ \
      frontend/ \
      proxy/ \
      .platform/ \
      -x "*/node_modules/*" \
      -x "*/.venv/*" \
      -x "*/__pycache__/*" \
      -x "*/.next/*" \
      -x "*/.git/*"
}

upload() {
  local s3_key="${APP_NAME}/versions/${VERSION_LABEL}.zip"
  info "Uploading to s3://${BUCKET}/${s3_key}"
  aws s3 cp "${ZIP_FILE}" "s3://${BUCKET}/${s3_key}"
}

deploy() {
  info "Deploying via Terraform (version: ${VERSION_LABEL})"
  cd "${INFRA_DIR}"
  terraform init -input=false \
      -backend-config="bucket=${BUCKET}" \
      -backend-config="region=${REGION}" \
      -backend-config="key=${APP_NAME}/terraform.tfstate"
  terraform apply -input=false -auto-approve \
      -var="eb_app_name=${APP_NAME}" \
      -var="app_version_label=${VERSION_LABEL}" \
      -var="tf_state_bucket=${BUCKET}"
}

package
upload
deploy

success "Deployment complete: ${VERSION_LABEL}"
