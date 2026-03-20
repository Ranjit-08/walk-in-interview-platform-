# modules/iam/main.tf
# IAM roles and policies for EC2 to access AWS services

# ── EC2 Instance Role ──────────────────────────────────────────────
resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })

  tags = { Name = "${var.project_name}-${var.environment}-ec2-role" }
}

# ── Custom Policy: SES ─────────────────────────────────────────────
resource "aws_iam_policy" "ses_policy" {
  name        = "${var.project_name}-${var.environment}-ses-policy"
  description = "Allow EC2 to send emails via SES"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = [
        "ses:SendEmail",
        "ses:SendRawEmail",
        "ses:GetSendQuota",
      ]
      Resource = "*"
    }]
  })
}

# ── Custom Policy: Bedrock ─────────────────────────────────────────
resource "aws_iam_policy" "bedrock_policy" {
  name        = "${var.project_name}-${var.environment}-bedrock-policy"
  description = "Allow EC2 to invoke Bedrock models"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListFoundationModels",
      ]
      Resource = "*"
    }]
  })
}

# ── Custom Policy: Cognito ─────────────────────────────────────────
resource "aws_iam_policy" "cognito_policy" {
  name        = "${var.project_name}-${var.environment}-cognito-policy"
  description = "Allow EC2 to manage Cognito users"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = [
        "cognito-idp:AdminGetUser",
        "cognito-idp:AdminDeleteUser",
        "cognito-idp:ListUsers",
        "cognito-idp:AdminUpdateUserAttributes",
      ]
      Resource = "*"
    }]
  })
}

# ── Custom Policy: S3 Frontend ─────────────────────────────────────
resource "aws_iam_policy" "s3_policy" {
  name        = "${var.project_name}-${var.environment}-s3-policy"
  description = "Allow EC2 read access to S3 frontend bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
      ]
      Resource = [
        "arn:aws:s3:::${var.bucket_name}",
        "arn:aws:s3:::${var.bucket_name}/*",
      ]
    }]
  })
}

# ── Attach all policies to the EC2 role ───────────────────────────
resource "aws_iam_role_policy_attachment" "ses" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.ses_policy.arn
}

resource "aws_iam_role_policy_attachment" "bedrock" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.bedrock_policy.arn
}

resource "aws_iam_role_policy_attachment" "cognito" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.cognito_policy.arn
}

resource "aws_iam_role_policy_attachment" "s3" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.s3_policy.arn
}

# SSM for secure remote access (no SSH needed in prod)
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# ── Instance Profile (attaches role to EC2) ────────────────────────
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-${var.environment}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}