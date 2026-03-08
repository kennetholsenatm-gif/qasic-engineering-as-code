# Outputs for wiring app config, Helm, or CI

output "deployment_target" {
  value = var.deployment_target
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

output "aws_secretsmanager_secret_name" {
  value       = var.deployment_target == "aws" && var.create_aws_rds ? aws_secretsmanager_secret.db[0].name : null
  description = "Secrets Manager secret name for DB credentials (for External Secrets Operator)"
}

output "aws_vpc_id" {
  value       = var.deployment_target == "aws" ? module.aws_networking[0].vpc_id : null
  description = "VPC ID for EKS/ECS placement"
}

output "aws_private_subnet_ids" {
  value       = var.deployment_target == "aws" ? module.aws_networking[0].private_subnet_ids : null
  description = "Private subnet IDs for RDS/ElastiCache/EKS"
}

# --- EKS (when create_aws_eks = true) ---

output "eks_cluster_name" {
  value       = var.deployment_target == "aws" && var.create_aws_eks ? module.aws_eks[0].cluster_name : null
  description = "EKS cluster name (for aws eks update-kubeconfig)"
}

output "eks_cluster_endpoint" {
  value       = var.deployment_target == "aws" && var.create_aws_eks ? module.aws_eks[0].cluster_endpoint : null
  description = "EKS API endpoint"
}

output "eks_oidc_provider_arn" {
  value       = var.deployment_target == "aws" && var.create_aws_eks ? module.aws_eks[0].oidc_provider_arn : null
  description = "EKS OIDC provider ARN (for IRSA)"
}
