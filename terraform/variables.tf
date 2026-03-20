# variables.tf — All input variables for the platform

variable "aws_region" {
  description = "AWS region to deploy all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name used as prefix for all resources"
  type        = string
  default     = "walkin-platform"
}

# ── VPC ────────────────────────────────────────────────────────────
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "availability_zones" {
  description = "Availability zones to use"
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]
}

# ── EC2 ────────────────────────────────────────────────────────────
variable "ec2_instance_type" {
  description = "EC2 instance type for the backend server"
  type        = string
  default     = "t3.small"
}

variable "ec2_key_pair_name" {
  description = "Name of the EC2 key pair for SSH access"
  type        = string
}

variable "ec2_ami_id" {
  description = "AMI ID for EC2 (Ubuntu 22.04 LTS ap-south-1)"
  type        = string
  default     = "ami-0f58b397bc5c1f2e8"
}

# ── RDS ────────────────────────────────────────────────────────────
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "MySQL database name"
  type        = string
  default     = "interview_platform"
}

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "admin"
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS in GB"
  type        = number
  default     = 20
}

# ── S3 ─────────────────────────────────────────────────────────────
variable "frontend_bucket_name" {
  description = "S3 bucket name for frontend static hosting"
  type        = string
  default     = "walkin-platform-frontend"
}

# ── Cognito ────────────────────────────────────────────────────────
variable "cognito_user_pool_name" {
  description = "Name for the Cognito User Pool"
  type        = string
  default     = "walkin-platform-users"
}

# ── SES ────────────────────────────────────────────────────────────
variable "ses_sender_email" {
  description = "Verified sender email address for SES"
  type        = string
}

# ── Domain (optional) ──────────────────────────────────────────────
variable "domain_name" {
  description = "Custom domain name (optional, leave empty to skip)"
  type        = string
  default     = ""
}