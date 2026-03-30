import os

from app.secrets import load_ssm_parameters

_ssm_prefix = os.environ.get("SSM_PREFIX", "")

if _ssm_prefix:
    _aws_region = os.environ.get("AWS_REGION", "")
    if not _aws_region:
        raise RuntimeError("AWS_REGION is required when SSM_PREFIX is set")
    load_ssm_parameters(prefix=_ssm_prefix, region=_aws_region)
