variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "db_subnet_group_name" {
  type = string
}

variable "db_security_group_id" {
  type = string
}

variable "rds_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "rds_db_name" {
  type    = string
  default = "whatwedoin"
}

variable "rds_username" {
  type = string
}

variable "rds_password" {
  type      = string
  sensitive = true
}
