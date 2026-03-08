# QASIC Engineering-as-Code: local development and full-stack targets
# OpenTofu is used only for cloud (AWS); local stack runs via Docker Compose here.
# On Windows without make: use "docker compose -f docker-compose.full.yml up -d --build" for full stack.

.PHONY: run-local down-local run-local-core down-local-core

# Full stack: API, frontend, Celery, Redis, Postgres, InfluxDB, MLflow, Grafana
# Copy .env.example to .env and set INFLUX_TOKEN if needed; defaults work otherwise.
run-local:
	docker compose -f docker-compose.full.yml up -d --build

down-local:
	docker compose -f docker-compose.full.yml down

# Core stack only: API, frontend, Celery, Redis, Postgres (no Influx/MLflow/Grafana)
run-local-core:
	docker compose up -d --build

down-local-core:
	docker compose down
