output "alb_dns_name" {
  description = "Public DNS of the Application Load Balancer — point your domain here"
  value       = aws_lb.main.dns_name
}

output "ecr_backend_url" {
  description = "ECR URL for the backend image"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_ml_service_url" {
  description = "ECR URL for the ML service image"
  value       = aws_ecr_repository.ml_service.repository_url
}

output "ecr_frontend_url" {
  description = "ECR URL for the frontend image"
  value       = aws_ecr_repository.frontend.repository_url
}

output "s3_uploads_bucket" {
  description = "S3 bucket for uploaded images"
  value       = aws_s3_bucket.uploads.bucket
}

output "s3_mlflow_bucket" {
  description = "S3 bucket for MLflow artifacts (models, metrics)"
  value       = aws_s3_bucket.mlflow.bucket
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}
