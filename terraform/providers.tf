# providers.tf — AWS provider configuration

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state stored in S3 (create this bucket manually before first apply)
  backend "s3" {
    bucket         = "walkin-platform-tfstate"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "walkin-interview-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}