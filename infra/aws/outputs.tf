# ── Outputs ───────────────────────────────────────────────────────────────

output "ecr_repository_url" {
  value       = aws_ecr_repository.agent.repository_url
  description = "ECR repository URL"
}

output "ecs_cluster_name" {
  value       = aws_ecs_cluster.agent.name
  description = "ECS cluster name"
}
