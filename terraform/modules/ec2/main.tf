# modules/ec2/main.tf — EC2 instance running the Flask backend

# ── User Data Script (bootstraps the server on first boot) ─────────
locals {
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    db_host           = var.db_host
    db_name           = var.db_name
    db_username       = var.db_username
    db_password       = var.db_password
    cognito_pool_id   = var.cognito_pool_id
    cognito_client_id = var.cognito_client_id
    ses_sender_email  = var.ses_sender_email
    frontend_url      = var.frontend_url
    aws_region        = var.aws_region
  }))
}

# ── EC2 Instance ───────────────────────────────────────────────────
resource "aws_instance" "backend" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [var.security_group_id]
  key_name               = var.key_pair_name
  iam_instance_profile   = var.iam_instance_profile

  user_data = local.user_data

  # Root volume: 20GB gp3
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    delete_on_termination = true
    encrypted             = true
  }

  # Enable detailed monitoring
  monitoring = true

  tags = {
    Name = "${var.project_name}-${var.environment}-backend"
    Role = "backend"
  }

  lifecycle {
    # Don't replace EC2 if user_data changes — use deploy script instead
    ignore_changes = [user_data]
  }
}

# ── Elastic IP (static IP for the backend) ─────────────────────────
resource "aws_eip" "backend" {
  instance   = aws_instance.backend.id
  domain     = "vpc"
  depends_on = [aws_instance.backend]

  tags = { Name = "${var.project_name}-${var.environment}-backend-eip" }
}

# ── API Gateway HTTP API → EC2 ─────────────────────────────────────
resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project_name}-${var.environment}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 300
  }

  tags = { Name = "${var.project_name}-${var.environment}-api" }
}

# ── VPC Link for private integration (optional — use HTTP for now) ──
resource "aws_apigatewayv2_integration" "ec2" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "HTTP_PROXY"
  integration_uri    = "http://${aws_eip.backend.public_ip}:5000/{proxy}"
  integration_method = "ANY"
}

# ── Catch-all route → EC2 ──────────────────────────────────────────
resource "aws_apigatewayv2_route" "proxy" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.ec2.id}"
}

# ── Default stage (auto-deploy) ────────────────────────────────────
resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "prod"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn

    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-stage"
  }
}

# ── CloudWatch Log Group for API Gateway ───────────────────────────
resource "aws_cloudwatch_log_group" "api_gw" {
  name              = "/aws/apigateway/${var.project_name}-${var.environment}"
  retention_in_days = 14
}

# ── CloudWatch Log Group for EC2 app ──────────────────────────────
resource "aws_cloudwatch_log_group" "app" {
  name              = "/app/${var.project_name}-${var.environment}"
  retention_in_days = 14
}