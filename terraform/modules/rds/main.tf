# modules/rds/main.tf — RDS MySQL 8.0 in private subnet

# ── Subnet Group (RDS needs at least 2 AZs) ───────────────────────
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet-group"
  subnet_ids = var.subnet_ids

  tags = { Name = "${var.project_name}-${var.environment}-db-subnet-group" }
}

# ── Parameter Group (MySQL 8.0 tuning) ────────────────────────────
resource "aws_db_parameter_group" "main" {
  name   = "${var.project_name}-${var.environment}-mysql8"
  family = "mysql8.0"

  parameter {
    name  = "character_set_server"
    value = "utf8mb4"
  }

  parameter {
    name  = "collation_server"
    value = "utf8mb4_unicode_ci"
  }

  parameter {
    name  = "max_connections"
    value = "200"
  }

  parameter {
    name  = "slow_query_log"
    value = "1"
  }

  parameter {
    name  = "long_query_time"
    value = "2"
  }

  tags = { Name = "${var.project_name}-${var.environment}-mysql8" }
}

# ── RDS MySQL Instance ─────────────────────────────────────────────
resource "aws_db_instance" "main" {
  identifier        = "${var.project_name}-${var.environment}-mysql"
  engine            = "mysql"
  engine_version    = "8.0"
  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.security_group_id]
  parameter_group_name   = aws_db_parameter_group.main.name

  # High availability
  multi_az = false  # Set to true for production HA

  # Backups
  backup_retention_period = 7           # Keep 7 days of backups
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  # Protection
  deletion_protection      = false      # Set true in production
  skip_final_snapshot      = false
  final_snapshot_identifier = "${var.project_name}-${var.environment}-final-snapshot"

  # Performance Insights
  performance_insights_enabled = false

  # Auto minor version upgrades
  auto_minor_version_upgrade = true

  publicly_accessible = false   # RDS stays in private subnet

  tags = { Name = "${var.project_name}-${var.environment}-mysql" }
}