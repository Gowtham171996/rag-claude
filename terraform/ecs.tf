resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"
  tags = local.common_tags

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name_prefix}-api"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "qdrant" {
  name              = "/ecs/${local.name_prefix}-qdrant"
  retention_in_days = 30
  tags              = local.common_tags
}

# ── API Task Definition ───────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name_prefix}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.api.repository_url}:${var.api_image_tag}"
    essential = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "QDRANT_HOST", value = "qdrant.${local.name_prefix}.local" },
      { name = "QDRANT_PORT", value = "6333" },
      { name = "LOG_LEVEL",   value = "INFO" },
    ]
    secrets = [
      { name = "ANTHROPIC_API_KEY", valueFrom = var.anthropic_api_key_secret_arn },
      { name = "VOYAGE_API_KEY",    valueFrom = var.voyage_api_key_secret_arn },
      { name = "API_KEY",           valueFrom = var.app_api_key_secret_arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
  tags = local.common_tags
}

# ── Qdrant Task Definition ────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "qdrant" {
  family                   = "${local.name_prefix}-qdrant"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  volume {
    name = "qdrant-data"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.qdrant.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.qdrant.id
        iam             = "ENABLED"
      }
    }
  }

  container_definitions = jsonencode([{
    name      = "qdrant"
    image     = "qdrant/qdrant:latest"
    essential = true
    portMappings = [
      { containerPort = 6333, protocol = "tcp" },
      { containerPort = 6334, protocol = "tcp" },
    ]
    mountPoints = [{ sourceVolume = "qdrant-data", containerPath = "/qdrant/storage" }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.qdrant.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "qdrant"
      }
    }
  }])
  tags = local.common_tags
}

# ── ECS Services ──────────────────────────────────────────────────────────────

resource "aws_service_discovery_private_dns_namespace" "main" {
  name = "${local.name_prefix}.local"
  vpc  = aws_vpc.main.id
  tags = local.common_tags
}

resource "aws_service_discovery_service" "qdrant" {
  name = "qdrant"
  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.main.id
    routing_policy = "MULTIVALUE"
    dns_records {
      ttl  = 10
      type = "A"
    }
  }
  tags = local.common_tags
}

resource "aws_ecs_service" "qdrant" {
  name            = "${local.name_prefix}-qdrant"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.qdrant.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.qdrant.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.qdrant.arn
  }

  tags = local.common_tags
}

resource "aws_ecs_service" "api" {
  name            = "${local.name_prefix}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  depends_on = [aws_ecs_service.qdrant]

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  tags = local.common_tags
}
