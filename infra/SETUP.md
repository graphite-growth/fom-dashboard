# Setup Guide

How to find the values needed for GitHub secrets.

## AWS Networking

```bash
# VPC ID — pick your target VPC
aws ec2 describe-vpcs --query "Vpcs[*].[VpcId, Tags[?Key=='Name'].Value | [0]]" --output table

# Subnets — list subnets for your VPC (use 2+ AZs for high availability)
aws ec2 describe-subnets --filters "Name=vpc-id,Values=<VPC_ID>" \
  --query "Subnets[*].[SubnetId, AvailabilityZone, Tags[?Key=='Name'].Value | [0]]" --output table

# Format subnet IDs as JSON arrays for GitHub:
#   APP_SUBNET_IDS:  '["subnet-aaa","subnet-bbb"]'
#   ELB_SUBNET_IDS:  '["subnet-aaa","subnet-bbb"]'

# Security group — list SGs in your VPC
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=<VPC_ID>" \
  --query "SecurityGroups[*].[GroupId, GroupName]" --output table
```

## Google OAuth

```bash
PROJECT_ID=$(gcloud config get-value project)
BRAND_ID=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
```

### Use existing credentials

```bash
gcloud alpha iap oauth-clients list "projects/${PROJECT_ID}/brands/${BRAND_ID}"
```

### Create new credentials

```bash
# 1. Create consent screen
gcloud alpha iap oauth-brands create \
  --application_title="FOM Dashboard" \
  --support_email="$(gcloud config get-value account)"

# 2. Create client
gcloud alpha iap oauth-clients create "projects/${PROJECT_ID}/brands/${BRAND_ID}" \
  --display_name="FOM Dashboard Web"

# 3. Add redirect URI in https://console.cloud.google.com/apis/credentials
#    → https://<your-domain>/api/v1/auth/callback
```

