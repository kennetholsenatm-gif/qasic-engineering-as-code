# QASIC Engineering-as-Code: OpenTofu IaC (AWS only)
# Provisions RDS, ElastiCache, Secrets Manager, and EKS for cloud deployment.
# Local stack: use Makefile or docker compose (see README).

# --- Dynamic DB password (when not provided) ---

resource "random_password" "db" {
  count   = var.deployment_target == "aws" && var.create_aws_rds && var.db_password == null ? 1 : 0
  length  = 32
  special = false
}

# --- AWS: Networking ---

module "aws_networking" {
  count  = var.deployment_target == "aws" ? 1 : 0
  source = "./modules/aws_networking"

  project_name = var.aws_project_name
  region       = var.aws_region
}

# --- AWS: RDS + ElastiCache ---

module "aws_data" {
  count  = var.deployment_target == "aws" ? 1 : 0
  source = "./modules/aws_data"

  project_name             = var.aws_project_name
  region                   = var.aws_region
  vpc_id                   = module.aws_networking[0].vpc_id
  private_subnet_ids       = module.aws_networking[0].private_subnet_ids
  data_security_group_id   = module.aws_networking[0].data_security_group_id
  db_username              = var.db_username
  db_password              = var.db_password != null ? var.db_password : (length(random_password.db) > 0 ? random_password.db[0].result : "")
  create_rds               = var.create_aws_rds
  create_elasticache       = var.create_aws_elasticache
}

# --- AWS: Store DB connection in Secrets Manager (for ESO / app config) ---

resource "aws_secretsmanager_secret" "db" {
  count       = var.deployment_target == "aws" && var.create_aws_rds ? 1 : 0
  name        = "${var.aws_project_name}-db-credentials"
  description = "QASIC RDS connection string (for External Secrets Operator or app)"
}

resource "aws_secretsmanager_secret_version" "db" {
  count         = var.deployment_target == "aws" && var.create_aws_rds ? 1 : 0
  secret_id     = aws_secretsmanager_secret.db[0].id
  secret_string = module.aws_data[0].database_url
}

# --- AWS: EKS (compute layer for Helm) ---

module "aws_eks" {
  count  = var.deployment_target == "aws" && var.create_aws_eks ? 1 : 0
  source = "./modules/aws_eks"

  project_name             = var.aws_project_name
  region                   = var.aws_region
  vpc_id                   = module.aws_networking[0].vpc_id
  private_subnet_ids       = module.aws_networking[0].private_subnet_ids
  data_security_group_id   = module.aws_networking[0].data_security_group_id
}
