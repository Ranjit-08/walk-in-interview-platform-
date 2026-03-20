# modules/ses/main.tf — SES email identity verification

# ── Verify sender email identity ───────────────────────────────────
resource "aws_ses_email_identity" "sender" {
  email = var.ses_sender_email
}

# ── SES sending policy ─────────────────────────────────────────────
resource "aws_ses_identity_policy" "sender_policy" {
  identity = aws_ses_email_identity.sender.arn
  name     = "${var.project_name}-${var.environment}-ses-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "*" }
      Action    = "SES:SendEmail"
      Resource  = aws_ses_email_identity.sender.arn
    }]
  })
}

# ── Configuration Set (for bounce/complaint tracking) ─────────────
resource "aws_ses_configuration_set" "main" {
  name = "${var.project_name}-${var.environment}-config"

  delivery_options {
    tls_policy = "Require"
  }

  reputation_metrics_enabled = true
  sending_enabled            = true
}