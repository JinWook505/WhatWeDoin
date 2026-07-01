terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "whatwedoin-tfstate"
    key            = "terraform.tfstate"
    region         = "ap-northeast-2"
    encrypt        = true
    dynamodb_table = "whatwedoin-tfstate-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ── ECR ─────────────────────────────────────────────────────────────────────
resource "aws_ecr_repository" "api" {
  name                 = var.ecr_repository
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

# ── Networking module ────────────────────────────────────────────────────────
module "networking" {
  source = "./modules/networking"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  acm_certificate_arn = var.acm_certificate_arn
}

# ── RDS module ───────────────────────────────────────────────────────────────
module "rds" {
  source = "./modules/rds"

  project_name        = var.project_name
  environment         = var.environment
  db_subnet_group_name = module.networking.db_subnet_group_name
  db_security_group_id = module.networking.db_security_group_id
  rds_instance_class  = var.rds_instance_class
  rds_db_name         = var.rds_db_name
  rds_username        = var.rds_username
  rds_password        = var.rds_password
}

# ── ECS module ───────────────────────────────────────────────────────────────
module "ecs" {
  source = "./modules/ecs"

  project_name          = var.project_name
  environment           = var.environment
  aws_region            = var.aws_region
  aws_account_id        = var.aws_account_id
  ecs_cluster_name      = var.ecs_cluster_name
  ecs_task_cpu          = var.ecs_task_cpu
  ecs_task_memory       = var.ecs_task_memory
  ecr_repository_url    = aws_ecr_repository.api.repository_url
  private_subnet_ids    = module.networking.private_subnet_ids
  ecs_security_group_id = module.networking.ecs_security_group_id
  target_group_arn      = module.networking.target_group_arn
  rds_endpoint          = module.rds.endpoint
  rds_db_name           = var.rds_db_name
  rds_username          = var.rds_username
  rds_password          = var.rds_password
}
