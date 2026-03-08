# Deployment target: "local" = Docker Compose on this machine; "aws" = cloud resources only (RDS, ElastiCache, etc.)

variable "deployment_target" {
  type        = string
  default     = "local"
  description = "Where to run the stack: local (docker-compose) or aws (managed DBs + optional ECS)"
  validation {
    condition     = contains(["local", "aws"], var.deployment_target)
    error_message = "deployment_target must be 'local' or 'aws'."
  }
}

variable "repo_root" {
  type        = string
  description = "Absolute path to the repo root (where docker-compose lives). Default: parent of infra/."
  default     = null
}

# --- Local (Docker Compose) ---

variable "compose_file" {
  type        = string
  default     = "docker-compose.full.yml"
  description = "Compose file name under repo_root (e.g. docker-compose.full.yml)"
}

variable "influx_token" {
  type        = string
  default     = "qasic-telemetry-token"
  description = "InfluxDB 2.x admin token for local stack"
  sensitive   = true
}

# --- AWS (when deployment_target = "aws") ---

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region for RDS, ElastiCache, etc."
}

variable "aws_project_name" {
  type        = string
  default     = "qasic"
  description = "Prefix for resource names (e.g. qasic-rds, qasic-cache)"
}

variable "db_username" {
  type        = string
  default     = "qasic"
  description = "PostgreSQL master username (AWS RDS)"
  sensitive   = true
}

variable "db_password" {
  type        = string
  description = "PostgreSQL master password (AWS RDS). Required when deployment_target = aws."
  default     = null
  sensitive   = true
}

variable "create_aws_elasticache" {
  type        = bool
  default     = true
  description = "When true and deployment_target=aws, create ElastiCache Redis"
}

variable "create_aws_rds" {
  type        = bool
  default     = true
  description = "When true and deployment_target=aws, create RDS PostgreSQL"
}
