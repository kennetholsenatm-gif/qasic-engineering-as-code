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

variable "data_security_group_id" {
  type        = string
  description = "Security group ID for RDS/Redis; nodes may need egress to this for app workloads"
}
