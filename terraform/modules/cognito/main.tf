# modules/cognito/main.tf — Cognito User Pool for auth

# ── User Pool ──────────────────────────────────────────────────────
resource "aws_cognito_user_pool" "main" {
  name = "${var.cognito_user_pool_name}-${var.environment}"

  # Use email as the username
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # Password policy
  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = false
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  # Email verification
  verification_message_template {
    default_email_option  = "CONFIRM_WITH_CODE"
    email_subject         = "Your Walk-in Interview Platform verification code"
    email_message         = "Your verification code is {####}. It expires in 24 hours."
  }

  # Account recovery via email
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Custom attributes
  schema {
    name                     = "role"
    attribute_data_type      = "String"
    mutable                  = true
    required                 = false
    string_attribute_constraints {
      min_length = 1
      max_length = 20
    }
  }

  # Email configuration (use SES in production)
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"  # Switch to SES after verification
  }

  # MFA (optional — off by default)
  mfa_configuration = "OFF"

  # User pool add-ons
  user_pool_add_ons {
    advanced_security_mode = "OFF"
  }

  tags = { Name = "${var.project_name}-${var.environment}-user-pool" }
}

# ── App Client ─────────────────────────────────────────────────────
resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.project_name}-${var.environment}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  # No client secret for SPA (browser-based auth)
  generate_secret = false

  # Auth flows allowed
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  # Token validity
  access_token_validity  = 24    # hours
  id_token_validity      = 24    # hours
  refresh_token_validity = 30    # days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # Read/write attributes
  read_attributes = [
    "email", "name", "phone_number",
    "custom:role",
  ]

  write_attributes = [
    "email", "name", "phone_number",
    "custom:role",
  ]

  # Prevent user existence errors leaking
  prevent_user_existence_errors = "ENABLED"
}

# ── User Pool Domain (for hosted UI if needed) ─────────────────────
resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.project_name}-${var.environment}-auth"
  user_pool_id = aws_cognito_user_pool.main.id
}