# modules/iam/variables.tf

variable "project_name" {
  description = "Project name prefix"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "bucket_name" {
  description = "S3 frontend bucket name"
  type        = string
}