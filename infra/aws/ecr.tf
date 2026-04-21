# ── ECR ───────────────────────────────────────────────────────────────────

resource "aws_ecr_repository" "agent" {
  name                 = local.name_prefix
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}
