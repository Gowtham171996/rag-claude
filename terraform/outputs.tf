output "alb_dns_name" {
  description = "ALB DNS name — point your domain's CNAME here"
  value       = aws_lb.main.dns_name
}

output "ecr_repository_url" {
  description = "ECR repository URL for docker push"
  value       = aws_ecr_repository.api.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name for CLI commands"
  value       = aws_ecs_cluster.main.name
}

output "api_service_name" {
  description = "ECS service name for force-new-deployment"
  value       = aws_ecs_service.api.name
}
