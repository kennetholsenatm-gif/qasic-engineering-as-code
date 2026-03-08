# Repo root: use variable if set, else assume we're in infra/tofu and go up two levels

locals {
  root = coalesce(var.repo_root, "${path.module}/../..")
  # For local-exec, we need a path that works from the machine running tofu (not from inside a container)
  compose_path = "${local.root}/${var.compose_file}"
}
