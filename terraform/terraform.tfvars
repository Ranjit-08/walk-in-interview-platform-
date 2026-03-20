# terraform.tfvars.example
# Copy to terraform.tfvars and fill in your values
# NEVER commit terraform.tfvars to git

aws_region   = "us-east-1"
environment  = "prod"
project_name = "walkin-platform"

# VPC
vpc_cidr             = "10.0.0.0/16"
public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24"]
availability_zones   = ["us-east-1a", "us-east-1b"]

# EC2
ec2_instance_type = "t3.small"
ec2_key_pair_name = "walkin-platform-key"
ec2_ami_id        = "ami-0c7217cdde317cfec"  # Ubuntu 22.04 us-east-1

# RDS
db_instance_class    = "db.t3.micro"
db_name              = "interview_platform"
db_username          = "admin"
db_password          = "Ranjit-1508"
db_allocated_storage = 20

# S3
frontend_bucket_name = "walkin-platform-frontend"

# Cognito
cognito_user_pool_name = "walkin-platform-users"

# SES — must be a verified email in AWS SES
ses_sender_email = "noreply@yourdomain.com"