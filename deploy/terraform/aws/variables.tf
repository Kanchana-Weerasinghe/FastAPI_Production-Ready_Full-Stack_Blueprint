variable "project" {
  description = "Short project name used in resource names"
  type        = string
  default     = "app"
}

variable "environment" {
  description = "staging or production"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "region" {
  type    = string
  default = "eu-west-1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "availability_zones" {
  type    = list(string)
  default = ["eu-west-1a", "eu-west-1b", "eu-west-1c"]
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "db_allocated_storage_gb" {
  type    = number
  default = 50
}

variable "db_multi_az" {
  description = "Standby in a second AZ with automatic failover (required for production)"
  type        = bool
  default     = true
}

variable "db_backup_retention_days" {
  description = "Automated backups + point-in-time recovery window"
  type        = number
  default     = 35
}

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.small"
}

variable "app_security_group_ids" {
  description = "Security groups of the workloads (e.g. EKS node/pod SGs) allowed to reach Postgres and Redis"
  type        = list(string)
  validation {
    condition     = length(var.app_security_group_ids) > 0
    error_message = "Provide at least one workload security group ID to grant private database and Redis access."
  }
}
