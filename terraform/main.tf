# main.tf — Root module: wires all sub-modules together

module "vpc" {
  source = "./modules/vpc"

  project_name         = var.project_name
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  availability_zones   = var.availability_zones
}

module "security_groups" {
  source = "./modules/security_groups"

  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.vpc.vpc_id
}

module "iam" {
  source = "./modules/iam"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
  bucket_name  = var.frontend_bucket_name
}

module "s3" {
  source = "./modules/s3"

  project_name  = var.project_name
  environment   = var.environment
  bucket_name   = var.frontend_bucket_name
}

module "rds" {
  source = "./modules/rds"

  project_name        = var.project_name
  environment         = var.environment
  db_instance_class   = var.db_instance_class
  db_name             = var.db_name
  db_username         = var.db_username
  db_password         = var.db_password
  db_allocated_storage = var.db_allocated_storage
  subnet_ids          = module.vpc.private_subnet_ids
  security_group_id   = module.security_groups.rds_sg_id
}

module "cognito" {
  source = "./modules/cognito"

  project_name           = var.project_name
  environment            = var.environment
  cognito_user_pool_name = var.cognito_user_pool_name
  ses_sender_email       = var.ses_sender_email
}

module "ses" {
  source = "./modules/ses"

  project_name     = var.project_name
  environment      = var.environment
  ses_sender_email = var.ses_sender_email
  aws_region       = var.aws_region
}

module "ec2" {
  source = "./modules/ec2"

  project_name      = var.project_name
  environment       = var.environment
  instance_type     = var.ec2_instance_type
  key_pair_name     = var.ec2_key_pair_name
  ami_id            = var.ec2_ami_id
  subnet_id         = module.vpc.public_subnet_ids[0]
  security_group_id = module.security_groups.ec2_sg_id
  iam_instance_profile = module.iam.ec2_instance_profile_name

  # Pass config to EC2 user_data via env vars
  db_host           = module.rds.endpoint
  db_name           = var.db_name
  db_username       = var.db_username
  db_password       = var.db_password
  cognito_pool_id   = module.cognito.user_pool_id
  cognito_client_id = module.cognito.app_client_id
  ses_sender_email  = var.ses_sender_email
  frontend_url      = module.s3.website_url
  aws_region        = var.aws_region
}