# Baseline AWS infrastructure for one environment: network, PostgreSQL, Redis, object storage and
# secrets. The Kubernetes cluster (EKS) and DNS/WAF/CDN are expected to be managed by your platform
# team's stack; wire them in through `app_security_group_ids` and the outputs below.

locals {
  name = "${var.project}-${var.environment}"
}

# --- Network: public subnets for load balancers only; app, database and cache in private subnets ----

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.16"

  name = local.name
  cidr = var.vpc_cidr
  azs  = var.availability_zones

  public_subnets   = [for i, _ in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, i)]
  private_subnets  = [for i, _ in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, i + 10)]
  database_subnets = [for i, _ in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, i + 20)]

  enable_nat_gateway           = true
  single_nat_gateway           = var.environment != "production"
  create_database_subnet_group = true

  enable_flow_log                      = true
  create_flow_log_cloudwatch_log_group = true
  create_flow_log_cloudwatch_iam_role  = true
}

# --- PostgreSQL (private, encrypted, multi-AZ, PITR) -----------------------------------------------

resource "aws_security_group" "db" {
  name        = "${local.name}-db"
  description = "PostgreSQL: only reachable from the application workloads"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "PostgreSQL from app"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.app_security_group_ids
  }
}

resource "random_password" "db_master" {
  length  = 40
  special = false
}

resource "aws_db_instance" "postgres" {
  identifier     = local.name
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage_gb
  max_allocated_storage = var.db_allocated_storage_gb * 4
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = replace(var.project, "-", "_")
  username = "app_admin"
  password = random_password.db_master.result

  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = var.db_multi_az

  backup_retention_period   = var.db_backup_retention_days
  backup_window             = "02:00-03:00"
  maintenance_window        = "sun:03:30-sun:04:30"
  copy_tags_to_snapshot     = true
  deletion_protection       = var.environment == "production"
  skip_final_snapshot       = var.environment != "production"
  final_snapshot_identifier = "${local.name}-final"

  performance_insights_enabled = true
  monitoring_interval          = 60
  monitoring_role_arn          = aws_iam_role.rds_monitoring.arn
  auto_minor_version_upgrade   = true

  parameter_group_name = aws_db_parameter_group.postgres.name
}

resource "aws_db_parameter_group" "postgres" {
  name   = "${local.name}-pg16"
  family = "postgres16"

  # Performance budget at the database: log statements slower than 500 ms.
  parameter {
    name  = "log_min_duration_statement"
    value = "500"
  }
  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "pending-reboot"
  }
}

resource "aws_iam_role" "rds_monitoring" {
  name = "${local.name}-rds-monitoring"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# --- Redis (rate limits, job queue): private, encrypted in transit and at rest ---------------------

resource "aws_security_group" "redis" {
  name        = "${local.name}-redis"
  description = "Redis: only reachable from the application workloads"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "Redis from app"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = var.app_security_group_ids
  }
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = local.name
  subnet_ids = module.vpc.private_subnets
}

resource "random_password" "redis_auth" {
  length  = 40
  special = false
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = local.name
  description                = "${local.name} rate limits and job queue"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = var.redis_node_type
  num_cache_clusters         = var.environment == "production" ? 2 : 1
  automatic_failover_enabled = var.environment == "production"
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis_auth.result
}

# --- Object storage for uploads: private, encrypted, versioned ------------------------------------

resource "aws_s3_bucket" "uploads" {
  bucket = "${local.name}-uploads"
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket                  = aws_s3_bucket.uploads.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    id     = "expire-noncurrent-versions"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# --- Secrets: generated here, rotated in Secrets Manager, synced to Kubernetes by External Secrets --

resource "random_password" "app_secret_key" {
  length  = 64
  special = false
}

resource "random_password" "field_encryption_key" {
  length  = 64
  special = false
}

resource "aws_secretsmanager_secret" "app" {
  name        = "${local.name}/app"
  description = "Runtime secrets of the ${local.name} API and worker"
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    SECRET_KEY           = random_password.app_secret_key.result
    FIELD_ENCRYPTION_KEY = random_password.field_encryption_key.result
    DB_HOST              = aws_db_instance.postgres.address
    DB_NAME              = aws_db_instance.postgres.db_name
    # Replace with the least-privilege roles from deploy/db/roles.sql after the first bootstrap.
    DB_USERNAME            = "app_admin"
    DB_PASSWORD            = random_password.db_master.result
    REDIS_URL              = "rediss://:${random_password.redis_auth.result}@${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/1"
    RATE_LIMIT_STORAGE_URI = "rediss://:${random_password.redis_auth.result}@${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/0"
  })

  # Values are managed in Secrets Manager after creation (rotation, manual edits).
  lifecycle {
    ignore_changes = [secret_string]
  }
}
