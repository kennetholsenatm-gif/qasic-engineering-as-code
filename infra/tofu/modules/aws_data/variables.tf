variable "project_name" {
  type = string
}

variable "region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "db_username" {
  type      = string
  sensitive = true
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "create_rds" {
  type    = bool
  default = true
}

variable "create_elasticache" {
  type    = bool
  default = true
}

variable "data_security_group_id" {
  type = string
}
