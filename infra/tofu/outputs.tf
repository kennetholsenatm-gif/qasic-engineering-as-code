# Outputs for wiring app config or CI

output "deployment_target" {
  value = var.deployment_target
}

# --- Local stack (when deployment_target = "local") ---

output "local_compose_status" {
  value       = var.deployment_target == "local" ? "docker compose up -d (see docker ps)" : null
  description = "Hint that the local stack was started via compose"
}

output "local_urls" {
  value = var.deployment_target == "local" ? {
    api      = "http://localhost:8000"
    frontend = "http://localhost:80"
    mlflow   = "http://localhost:5000"
    influx   = "http://localhost:8086"
  } : null
}

output "local_database_url" {
  value     = var.deployment_target == "local" ? "postgresql://qasic:qasic@localhost:5432/qasic" : null
  sensitive = true
}

output "local_celery_broker_url" {
  value     = var.deployment_target == "local" ? "redis://localhost:6379/0" : null
  sensitive = true
}

output "local_mlflow_tracking_uri" {
  value = var.deployment_target == "local" ? "http://localhost:5000" : null
}

output "local_influx_url" {
  value = var.deployment_target == "local" ? "http://localhost:8086" : null
}

# --- AWS (when deployment_target = "aws") ---

output "aws_database_url" {
  value       = var.deployment_target == "aws" ? module.aws_data[0].database_url : null
  sensitive   = true
  description = "PostgreSQL connection string for RDS"
}

output "aws_celery_broker_url" {
  value       = var.deployment_target == "aws" ? module.aws_data[0].celery_broker_url : null
  sensitive   = true
  description = "Redis URL for Celery (ElastiCache)"
}

output "aws_vpc_id" {
  value       = var.deployment_target == "aws" ? module.aws_networking[0].vpc_id : null
  description = "VPC ID for ECS/EC2 placement"
}

output "aws_private_subnet_ids" {
  value       = var.deployment_target == "aws" ? module.aws_networking[0].private_subnet_ids : null
  description = "Private subnet IDs for RDS/ElastiCache/ECS"
}
