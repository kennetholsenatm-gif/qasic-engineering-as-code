# RDS PostgreSQL + ElastiCache Redis for QASIC stack (when pushing to cloud)

# --- RDS (PostgreSQL) ---

resource "aws_db_subnet_group" "main" {
  count       = var.create_rds ? 1 : 0
  name_prefix = "${var.project_name}-"
  subnet_ids  = var.private_subnet_ids
  tags        = { Name = "${var.project_name}-db-subnets" }
}

resource "aws_db_parameter_group" "main" {
  count       = var.create_rds ? 1 : 0
  family      = "postgres15"
  name_prefix = "${var.project_name}-"
  tags        = { Name = "${var.project_name}-pg15" }
}

resource "aws_db_instance" "main" {
  count = var.create_rds ? 1 : 0

  identifier     = "${var.project_name}-postgres"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.micro"

  allocated_storage     = 20
  max_allocated_storage  = 100
  storage_encrypted      = true

  db_name  = "qasic"
  username = var.db_username
  password = var.db_password
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.main[0].name
  vpc_security_group_ids = [var.data_security_group_id]
  publicly_accessible    = false
  multi_az               = false

  parameter_group_name = aws_db_parameter_group.main[0].name
  skip_final_snapshot  = true
  tags                = { Name = "${var.project_name}-rds" }
}

# --- ElastiCache (Redis) ---

resource "aws_elasticache_subnet_group" "main" {
  count       = var.create_elasticache ? 1 : 0
  name        = "${var.project_name}-redis-subnets"
  subnet_ids  = var.private_subnet_ids
  description = "Subnets for ${var.project_name} Redis"
}

resource "aws_elasticache_cluster" "main" {
  count = var.create_elasticache ? 1 : 0

  cluster_id           = "${var.project_name}-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.main[0].name
  security_group_ids = [var.data_security_group_id]
  tags               = { Name = "${var.project_name}-redis" }
}
