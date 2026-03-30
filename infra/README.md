# Infrastructure

```
infra/
├── oidc/   # Bootstrap: S3 state bucket, GitHub OIDC provider, deploy IAM role
└── app/    # Application: Elastic Beanstalk, RDS, Route 53, ACM
```

## First-Time Setup

1. Configure AWS credentials locally (`aws configure` or SSO)
2. Install [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.10 and the [GitHub CLI](https://cli.github.com/)
3. Run the bootstrap script:

```bash
bash scripts/bootstrap-oidc.sh
```

This creates the S3 state bucket, OIDC provider, and deploy role, then sets the required GitHub secrets automatically.

## Deploying

Pushes to `main` trigger a deploy via GitHub Actions. To deploy manually:

```bash
gh workflow run deploy.yml
```

## Manual Terraform Operations

```bash
# Bootstrap (OIDC + state bucket) — local state
cd infra/oidc
terraform init
terraform plan
terraform apply

# Application — remote S3 state
cd infra/app
terraform init \
  -backend-config="bucket=$TF_STATE_BUCKET" \
  -backend-config="region=$TF_STATE_REGION" \
  -backend-config="key=fom_dashboard/terraform.tfstate"
terraform plan
terraform apply
```
