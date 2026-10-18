output "vpc_id" {
  value = module.vpc.vpc_id
}

output "private_subnet_ids" {
  value = module.vpc.private_subnets
}

output "db_endpoint" {
  value = aws_db_instance.postgres.address
}

output "redis_endpoint" {
  value = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "uploads_bucket" {
  value = aws_s3_bucket.uploads.bucket
}

output "app_secret_arn" {
  description = "Reference this from an ExternalSecret to create the Kubernetes Secret used by the Helm chart"
  value       = aws_secretsmanager_secret.app.arn
}
