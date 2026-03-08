# OpenTofu 1.6+ (Terraform-compatible). Use: tofu init && tofu plan && tofu apply

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Optional: remote backend for state (e.g. when pushing to cloud)
  # backend "s3" {
  #   bucket         = "qasic-tofu-state"
  #   key            = "tofu/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "qasic-tofu-lock"
  # }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project = "qasic-engineering"
    }
  }
}
