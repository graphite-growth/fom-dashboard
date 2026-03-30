
# Equivalent to `openssl rand -base64 32`; 256-bit key for signing JWTs.
resource "random_bytes" "auth_secret" {
  length = 32
}

resource "aws_elastic_beanstalk_application" "_" {
  name        = var.eb_app_name
  description = "${var.project_name} application"

  appversion_lifecycle {
    service_role          = aws_iam_role.eb_service.arn
    max_count             = 10
    delete_source_from_s3 = true
  }
}

resource "aws_elastic_beanstalk_environment" "_" {
  name                = var.eb_environment_name
  application         = aws_elastic_beanstalk_application._.name
  solution_stack_name = var.solution_stack_name

  # VPC
  setting {
    namespace = "aws:ec2:vpc"
    name      = "VPCId"
    value     = var.vpc_id
  }

  setting {
    namespace = "aws:ec2:vpc"
    name      = "Subnets"
    value     = join(",", var.app_subnet_ids)
  }

  # Instances
  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "InstanceType"
    value     = var.instance_type
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "IamInstanceProfile"
    value     = aws_iam_instance_profile._.name
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "SecurityGroups"
    value     = var.security_group_id
  }

  # Service role
  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "ServiceRole"
    value     = aws_iam_role.eb_service.arn
  }

  # Single instance (no load balancer — CloudFront handles HTTPS)
  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "EnvironmentType"
    value     = "SingleInstance"
  }

  # Pin autoscaling to exactly 1 instance
  setting {
    namespace = "aws:autoscaling:asg"
    name      = "MinSize"
    value     = "1"
  }

  setting {
    namespace = "aws:autoscaling:asg"
    name      = "MaxSize"
    value     = "1"
  }

  # Health check
  setting {
    namespace = "aws:elasticbeanstalk:application"
    name      = "Application Healthcheck URL"
    value     = "/api/v1/health"
  }

  # Environment variables
  # Secrets are stored in SSM Parameter Store and loaded by the app at startup.
  # SSM_PREFIX tells the app where to find them.
  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "SSM_PREFIX"
    value     = var.ssm_prefix
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "AWS_REGION"
    value     = var.region
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "ALLOWED_DOMAIN"
    value     = var.allowed_domain
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "DEV_AUTH"
    value     = "false"
  }




  tags = {
    Name = "${var.project_name}-eb-env"
  }

  lifecycle {
    ignore_changes = [version_label]
  }
}




resource "terraform_data" "_" {
  triggers_replace = {
    environment_cname = aws_elastic_beanstalk_environment._.cname
  }

  provisioner "local-exec" {
    command = <<-EOT
      aws elasticbeanstalk update-environment \
        --environment-name ${aws_elastic_beanstalk_environment._.name} \
        --option-settings "Namespace=aws:elasticbeanstalk:application:environment,OptionName=AUTH_URL,Value=http://${aws_elastic_beanstalk_environment._.cname}" \
        --region ${var.region}
    EOT
  }
}




resource "aws_elastic_beanstalk_application_version" "_" {
  count       = var.app_version_label != "" ? 1 : 0
  name        = var.app_version_label
  application = aws_elastic_beanstalk_application._.name
  bucket      = var.tf_state_bucket
  key         = "${var.eb_app_name}/versions/${var.app_version_label}.zip"
}

resource "terraform_data" "deploy" {
  count = var.app_version_label != "" ? 1 : 0

  triggers_replace = {
    version_label = var.app_version_label
  }

  provisioner "local-exec" {
    command = <<-EOT
      aws elasticbeanstalk update-environment \
        --environment-name ${aws_elastic_beanstalk_environment._.name} \
        --version-label ${var.app_version_label} \
        --region ${var.region}
      aws elasticbeanstalk wait environment-updated \
        --environment-names ${aws_elastic_beanstalk_environment._.name} \
        --region ${var.region}
    EOT
  }

  depends_on = [aws_elastic_beanstalk_application_version._]
}

