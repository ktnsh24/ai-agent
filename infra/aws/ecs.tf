# ── ECS Cluster ───────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "agent" {
  name = local.name_prefix
  tags = local.common_tags

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ── ECS Task Definition ──────────────────────────────────────────────────

resource "aws_ecs_task_definition" "agent" {
  family                   = local.name_prefix
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_cpu
  memory                   = var.ecs_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "agent"
    image     = "${aws_ecr_repository.agent.repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 8200
      protocol      = "tcp"
    }]

    environment = [
      { name = "CLOUD_PROVIDER", value = "aws" },
      { name = "APP_ENVIRONMENT", value = var.environment },
      { name = "AWS_DEFAULT_REGION", value = var.aws_region },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.agent.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])

  tags = local.common_tags
}

# ── ECS Service ───────────────────────────────────────────────────────────

resource "aws_ecs_service" "agent" {
  name            = local.name_prefix
  cluster         = aws_ecs_cluster.agent.id
  task_definition = aws_ecs_task_definition.agent.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public.id]
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  tags = local.common_tags
}
