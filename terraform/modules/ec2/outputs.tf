# modules/ec2/outputs.tf — Outputs from the EC2 module

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.backend.id
}

output "public_ip" {
  description = "Elastic IP address of the backend server"
  value       = aws_eip.backend.public_ip
}

output "public_dns" {
  description = "Public DNS of the EC2 instance"
  value       = aws_eip.backend.public_dns
}

output "api_gateway_url" {
  description = "API Gateway invoke URL — use this in frontend api.js as API_BASE"
  value       = aws_apigatewayv2_stage.prod.invoke_url
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.main.id
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name for the Flask app"
  value       = aws_cloudwatch_log_group.app.name
}