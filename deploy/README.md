# QASIC Deployment

## Kubernetes (cloud-agnostic)

The recommended production path is **Kubernetes** with the provided **Helm** chart. The same chart runs on:

| Target | Notes |
|--------|--------|
| **AWS** | EKS – provision cluster, then `helm install` |
| **GCP** | GKE – same |
| **Azure** | AKS – same |
| **OpenNebula** | OneKE (OpenNebula Kubernetes Engine) – use OpenTofu/Terraform with the OpenNebula provider to create the cluster, then `helm install` |
| **Bare metal** | Any CNCF-certified Kubernetes |

### What the chart includes

- **Helm** packaging for API, Frontend, Celery workers, Redis, Postgres.
- **KEDA** (Kubernetes Event-driven Autoscaling) to scale Celery workers based on Redis queue length. Works on any K8s cluster.
- Optional **MLflow** and **Grafana** (enable via values).

### Quick start

See **[deploy/helm/qasic/README.md](helm/qasic/README.md)** for install steps, KEDA tuning, OneKE, and Ingress.

```bash
# Install KEDA once per cluster, then install the app chart
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda -n keda --create-namespace

helm install qasic ./deploy/helm/qasic -n qasic --create-namespace \
  --set image.registry=your-registry/ \
  --set image.api.repository=qasic-api \
  --set image.frontend.repository=qasic-frontend \
  --set api.shortServiceName=true
```

## CI/CD and ECR

Hardware CI (`.github/workflows/hardware-ci.yml`) runs tests, pipeline, Trivy container scanning, and **uploads SARIF** to GitHub so container vulnerabilities appear in the Security tab and PR checks. On push to `main`/`master`, if repository variable **ENABLE_ECR_PUSH** is set to `true` and secret **AWS_ROLE_TO_ASSUME** is configured (OIDC), the workflow builds and pushes API and frontend images to Amazon ECR with tags `${{ github.sha }}` and `latest`. Create ECR repositories `qasic-api` and `qasic-frontend` (via Tofu or console), then reference the image in Helm, e.g. `--set image.registry=<account>.dkr.ecr.<region>.amazonaws.com/ --set image.api.tag=<sha>`.

## Docker Compose (local / dev)

- **docker-compose.yml** – Core stack: API, Frontend, Celery, Redis, Postgres (production parity).
- **docker-compose.full.yml** – Core + InfluxDB, MLflow, Grafana.

Use `make run-local` or `make run-local-core` from repo root (see main README). Not suitable for multi-tenant or horizontal scaling; use Kubernetes for that.
