variable "project_name"         { type = string }
variable "environment"          { type = string }
variable "instance_type"        { type = string }
variable "ami_id"               { type = string }
variable "subnet_id"            { type = string }
variable "security_group_id"    { type = string }
variable "iam_instance_profile" { type = string }
variable "db_host"              { type = string }
variable "db_name"              { type = string }
variable "db_username"          { type = string }
variable "db_password" {
  type      = string
  sensitive = true
}
variable "cognito_pool_id"      { type = string }
variable "cognito_client_id"    { type = string }
variable "ses_sender_email"     { type = string }
variable "frontend_url"         { type = string }
variable "aws_region"           { type = string }
variable "key_pair_name" {
  type    = string
  default = ""
}
