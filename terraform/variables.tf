variable "aws_region" {
  description = "AWS region (Seoul)"
  type        = string
  default     = "ap-northeast-2"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "project_name" {
  description = "Resource naming prefix"
  type        = string
  default     = "whatwedoin"
}

variable "environment" {
  description = "Deployment environment (dev or prod)"
  type        = string
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be 'dev' or 'prod'."
  }
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of AZs for subnets (minimum 2)"
  type        = list(string)
  default     = ["ap-northeast-2a", "ap-northeast-2c"]
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for ALB HTTPS listener"
  type        = string
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID for domain"
  type        = string
  default     = ""
}

# ECR
variable "ecr_repository" {
  description = "ECR repository name for the backend image"
  type        = string
  default     = "whatwedoin-api"
}

# ECS
variable "ecs_cluster_name" {
  description = "ECS cluster name"
  type        = string
  default     = "whatwedoin-cluster"
}

variable "ecs_task_cpu" {
  description = "Fargate task CPU units"
  type        = number
  default     = 512
}

variable "ecs_task_memory" {
  description = "Fargate task memory (MiB)"
  type        = number
  default     = 1024
}

# RDS
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "rds_db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "whatwedoin"
}

variable "rds_username" {
  description = "RDS master username"
  type        = string
}

variable "rds_password" {
  description = "RDS master password (sensitive)"
  type        = string
  sensitive   = true
}
