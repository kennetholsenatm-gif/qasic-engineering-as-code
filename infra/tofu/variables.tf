# Deployment target: "aws" = provision RDS, ElastiCache, EKS; local stack uses Makefile/Compose (no Tofu).

variable "deployment_target" {
  type        = string
  default     = "aws"
  description = "Cloud target: aws (RDS, ElastiCache, EKS). For local dev use make run-local or docker compose."
  validation {
    condition     = contains(["aws"], var.deployment_target)
    error_message = "deployment_target must be 'aws'."
  }
}

# --- AWS ---

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region for RDS, ElastiCache, EKS"
}

variable "aws_project_name" {
  type        = string
  default     = "qasic"
  description = "Prefix for resource names (e.g. qasic-rds, qasic-eks)"
}

variable "db_username" {
  type        = string
  default     = "qasic"
  description = "PostgreSQL master username (AWS RDS)"
  sensitive   = true
}

variable "db_password" {
  type        = string
  description = "PostgreSQL master password (AWS RDS). If unset, Tofu generates one and stores it in Secrets Manager."
  default     = null
  sensitive   = true
}

variable "create_aws_rds" {
  type        = bool
  default     = true
  description = "When true and deployment_target=aws, create RDS PostgreSQL"
}

variable "create_aws_elasticache" {
  type        = bool
  default     = true
  description = "When true and deployment_target=aws, create ElastiCache Redis"
}

variable "create_aws_eks" {
  type        = bool
  default     = true
  description = "When true and deployment_target=aws, create EKS cluster for Helm deployment"
}
