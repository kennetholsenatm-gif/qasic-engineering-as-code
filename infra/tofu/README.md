# QASIC Engineering-as-Code – OpenTofu IaC

Deploy the full stack (API, Celery, Redis, PostgreSQL, InfluxDB, MLflow, frontend) **locally** via Docker Compose, or provision **cloud** resources (AWS RDS + ElastiCache) and point your containers at them.

## Prerequisites

- **Local:** [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- **OpenTofu:** [Install OpenTofu](https://opentofu.org/docs/intro/install/) (1.6+) or use Terraform 1.6+
- **AWS (optional):** Only when using `deployment_target = "aws"` — AWS CLI configured (`aws configure`). For local-only you do not need AWS credentials.

## Quick start (local stack)

From the **repo root**:

```bash
# Option A: OpenTofu drives Docker Compose
cd infra/tofu
tofu init
tofu apply -var="deployment_target=local"
# When prompted, type yes. This generates .env.tofu and runs:
#   docker compose -f docker-compose.full.yml --env-file .env.tofu up -d --build
```

From the **repo root** (without OpenTofu):

```bash
# Option B: Docker Compose only
docker compose -f docker-compose.full.yml up -d --build
```

Then open:

- **Frontend:** http://localhost:80  
- **API / Swagger:** http://localhost:8000/docs  
- **MLflow:** http://localhost:5000  
- **InfluxDB:** http://localhost:8086  

API and Celery worker use:

- `DATABASE_URL=postgresql://qasic:qasic@postgres:5432/qasic`
- `CELERY_BROKER_URL=redis://redis:6379/0`
- `MLFLOW_TRACKING_URI=http://mlflow:5000`
- `INFLUX_URL=http://influxdb:8086` (token in `.env.tofu` or `INFLUX_TOKEN`)

## OpenTofu workflow

| Command | Purpose |
|--------|---------|
| `tofu init` | Download providers (null, local, docker, aws) |
| `tofu plan -var="deployment_target=local"` | Preview local compose run |
| `tofu apply -var="deployment_target=local"` | Generate `.env.tofu` and run `docker compose up -d` |
| `tofu destroy -var="deployment_target=local"` | Run `docker compose down` and remove `.env.tofu` |
| `tofu output` | Show URLs and connection strings |

### Windows

If `tofu apply` fails on Windows (e.g. missing `sh`), run Compose yourself from the repo root:

```powershell
docker compose -f docker-compose.full.yml up -d --build
```

Use `tofu output` to see the same URLs; the OpenTofu state will still track the `local_file` and `null_resource`.

## Push to cloud (AWS)

Provision **RDS (PostgreSQL)** and **ElastiCache (Redis)** so you can run the API and Celery worker in ECS, Lambda, or on EC2 and point them at managed DBs.

1. Set a DB password and apply:

   ```bash
   cd infra/tofu
   tofu init
   tofu apply -var="deployment_target=aws" -var="db_password=YourSecurePassword"
   ```

2. After apply, wire your app to the outputs:

   ```bash
   tofu output -json
   # Use: aws_database_url, aws_celery_broker_url
   ```

3. Run your containers (e.g. push images to ECR and run ECS tasks) with:

   - `DATABASE_URL=$(tofu output -raw aws_database_url)`
   - `CELERY_BROKER_URL=$(tofu output -raw aws_celery_broker_url)`

InfluxDB and MLflow are not created in AWS by this module; you can add them (e.g. EC2 or managed offerings) or keep them local/separate.

## Layout

```
infra/tofu/
├── versions.tf      # OpenTofu 1.6+, providers (null, local, docker, aws)
├── variables.tf     # deployment_target, repo_root, compose_file, aws_*, db_*
├── locals.tf        # repo root path, compose path
├── main.tf          # local: .env.tofu + null_resource compose; aws: modules
├── outputs.tf       # local_urls, local_database_url, aws_database_url, etc.
├── README.md
└── modules/
    ├── aws_networking/   # VPC, subnets, security group for RDS/Redis
    └── aws_data/         # RDS PostgreSQL, ElastiCache Redis
```

## Backend (optional)

To keep state in S3 (e.g. for team or CI), uncomment and set the `backend "s3"` block in `versions.tf`, then run `tofu init -reconfigure` and `tofu apply` as usual.
