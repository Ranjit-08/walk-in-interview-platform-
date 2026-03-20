# outputs.tf — Key values printed after terraform apply

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "ec2_public_ip" {
  description = "Public IP of the EC2 backend server"
  value       = module.ec2.public_ip
}

output "ec2_public_dns" {
  description = "Public DNS of the EC2 backend server"
  value       = module.ec2.public_dns
}

output "rds_endpoint" {
  description = "RDS MySQL endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "s3_bucket_name" {
  description = "S3 bucket name for frontend"
  value       = module.s3.bucket_name
}

output "s3_website_url" {
  description = "S3 static website URL"
  value       = module.s3.website_url
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = module.cognito.user_pool_id
}

output "cognito_app_client_id" {
  description = "Cognito App Client ID"
  value       = module.cognito.app_client_id
}

output "api_gateway_url" {
  description = "API Gateway invoke URL"
  value       = module.ec2.api_gateway_url
}

output "backend_env_file" {
  description = "Copy this into your backend .env file"
  sensitive   = true
  value       = <<-EOT
    DB_HOST=${module.rds.endpoint}
    DB_NAME=${var.db_name}
    DB_USER=${var.db_username}
    DB_PASSWORD=${var.db_password}
    COGNITO_USER_POOL_ID=${module.cognito.user_pool_id}
    COGNITO_APP_CLIENT_ID=${module.cognito.app_client_id}
    SES_SENDER_EMAIL=${var.ses_sender_email}
    FRONTEND_URL=${module.s3.website_url}
    AWS_REGION=${var.aws_region}
  EOT
}