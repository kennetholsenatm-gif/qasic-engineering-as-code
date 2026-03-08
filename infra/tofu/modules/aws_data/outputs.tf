output "database_url" {
  value = var.create_rds ? "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.main[0].address}:${aws_db_instance.main[0].port}/qasic" : null
  sensitive = true
}

output "rds_endpoint" {
  value = var.create_rds ? aws_db_instance.main[0].address : null
}

output "celery_broker_url" {
  value = var.create_elasticache ? "redis://${aws_elasticache_cluster.main[0].cache_nodes[0].address}:6379/0" : null
  sensitive = true
}

output "redis_endpoint" {
  value = var.create_elasticache ? aws_elasticache_cluster.main[0].cache_nodes[0].address : null
}
