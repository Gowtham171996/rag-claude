resource "aws_efs_file_system" "qdrant" {
  encrypted = true
  tags      = merge(local.common_tags, { Name = "${local.name_prefix}-qdrant-efs" })
}

resource "aws_efs_mount_target" "qdrant" {
  count           = 2
  file_system_id  = aws_efs_file_system.qdrant.id
  subnet_id       = aws_subnet.private[count.index].id
  security_groups = [aws_security_group.qdrant.id]
}

resource "aws_efs_access_point" "qdrant" {
  file_system_id = aws_efs_file_system.qdrant.id
  posix_user {
    gid = 1000
    uid = 1000
  }
  root_directory {
    path = "/qdrant"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }
  tags = local.common_tags
}
