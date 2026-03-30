
output "eb_app_name" {
  description = "Elastic Beanstalk application name"
  value       = aws_elastic_beanstalk_application._.name
}

output "eb_environment_name" {
  description = "Elastic Beanstalk environment name"
  value       = aws_elastic_beanstalk_environment._.name
}

output "eb_environment_cname" {
  description = "Elastic Beanstalk environment CNAME"
  value       = aws_elastic_beanstalk_environment._.cname
}




