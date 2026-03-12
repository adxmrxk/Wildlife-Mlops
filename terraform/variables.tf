variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project prefix used for naming all resources"
  type        = string
  default     = "wildlife-mlops"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "db_password" {
  description = "PostgreSQL master password — set via TF_VAR_db_password env var"
  type        = string
  sensitive   = true
}

variable "backend_image" {
  description = "ECR image URI for the Spring Boot backend"
  type        = string
}

variable "ml_service_image" {
  description = "ECR image URI for the FastAPI ML service"
  type        = string
}

variable "frontend_image" {
  description = "ECR image URI for the React frontend (nginx)"
  type        = string
}

variable "mlflow_image" {
  description = "ECR image URI for the MLflow tracking server"
  type        = string
}
