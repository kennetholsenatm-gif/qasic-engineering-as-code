# QASIC Helm Chart (Cloud-Agnostic Kubernetes)

This Helm chart packages the QASIC Engineering-as-Code stack for **Kubernetes**. The same manifests run on:

- **AWS** (EKS)
- **GCP** (GKE)
- **Azure** (AKS)
- **OpenNebula** (OneKE – OpenNebula Kubernetes Engine)
- **Bare metal** (any CNCF-certified K8s)

## Strategy

- **Helm** packages API, Frontend, Celery workers, Redis, Postgres, and optional MLflow/Grafana.
- **KEDA** (Kubernetes Event-driven Autoscaling) scales `celery-worker` based on Redis queue length. KEDA works on any K8s cluster (no cloud lock-in).
- Use **OpenTofu/Terraform** with the OpenNebula provider to provision a OneKE cluster, then install this chart. On public clouds, provision EKS/GKE/AKS and install the same chart.

## Prerequisites

- Kubernetes 1.24+
- Helm 3
- **KEDA** installed in the cluster (for Celery autoscaling). Install with:
  ```bash
  helm repo add kedacore https://kedacore.github.io/charts
  helm install keda kedacore/keda --namespace keda --create-namespace
  ```

## Install

1. Build and push images (or use existing registry):
   ```bash
   docker build -f Dockerfile.api -t your-registry/qasic-api:0.1.0 .
   docker build -f Dockerfile.frontend -t your-registry/qasic-frontend:0.1.0 .
   docker push your-registry/qasic-api:0.1.0
   docker push your-registry/qasic-frontend:0.1.0
   ```

2. Install the chart:
   ```bash
   helm install qasic ./deploy/helm/qasic \
     --namespace qasic --create-namespace \
     --set image.registry=your-registry/ \
     --set image.api.repository=qasic-api \
     --set image.api.tag=0.1.0 \
     --set image.frontend.repository=qasic-frontend \
     --set image.frontend.tag=0.1.0 \
     --set api.shortServiceName=true
   ```
   `api.shortServiceName=true` creates a Service named `api` so the frontend (nginx `proxy_pass http://api:8000`) can reach the API in-cluster. Use one release per namespace.

3. (Optional) Use external Redis/Postgres (e.g. ElastiCache, RDS):
   ```bash
   --set redis.enabled=false \
   --set redis.externalHost=my-redis.example.com:6379 \
   --set postgres.enabled=false \
   --set postgres.externalUrl=postgresql://user:pass@rds-host:5432/qasic
   ```
   When `redis.enabled=false`, you must set `CELERY_BROKER_URL` (and optionally `CELERY_RESULT_BACKEND`) via `api.env` / `celeryWorker.env` or an existing Secret.

## KEDA (Celery autoscaling)

When `keda.enabled=true` (default) and `redis.enabled=true`, a KEDA `ScaledObject` scales the `celery-worker` Deployment based on the length of the Redis list `celery` (Celery’s default queue).

- **listLengthTarget**: target tasks per worker; scale up when queue length exceeds this.
- **minReplicaCount** / **maxReplicaCount**: from `replicaCount.celeryWorker.min` / `max`.

Adjust in `values.yaml` or via `--set`:

```bash
--set keda.listLengthTarget=10 \
--set replicaCount.celeryWorker.max=20
```

## OpenNebula (OneKE)

1. Use OpenTofu/Terraform with the [OpenNebula provider](https://registry.terraform.io/providers/OpenNebula/opennebula/latest) to create a OneKE cluster.
2. Configure `kubectl` for the OneKE cluster.
3. Install KEDA and this Helm chart as above. No chart changes are required.

## Ingress

Enable and configure Ingress for external access (e.g. ALB on AWS, Ingress controller on OneKE):

```bash
helm upgrade qasic ./deploy/helm/qasic -n qasic \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set ingress.hosts[0].host=qasic.example.com
```

## Optional: MLflow and Grafana

```bash
--set mlflow.enabled=true \
--set grafana.enabled=true \
--set grafana.adminPassword=changeme
```

## High availability (HPA and PDB)

- **HPA:** Enable for API and frontend to scale on CPU: `api.hpa.enabled=true`, `frontend.hpa.enabled=true`. Tune `minReplicas`, `maxReplicas`, `targetCPUUtilizationPercentage`.
- **PDB:** Enable to ensure availability during node drains: `api.pdb.enabled=true`, `frontend.pdb.enabled=true`, `minAvailable: 1`.

## Network policies

Set `networkPolicy.enabled=true` to apply default-deny ingress and explicit allow rules (frontend→API, API/Celery→Postgres, API/Celery→Redis). Requires a CNI that supports NetworkPolicy (e.g. Calico, Cilium).

## External Secrets Operator (ESO)

For production, avoid plaintext passwords in values. Use ESO to sync credentials from AWS Secrets Manager (or other backends) into Kubernetes Secrets.

1. Install [External Secrets Operator](https://external-secrets.io/) and configure a `ClusterSecretStore` for AWS (e.g. IRSA or access key).
2. Set `postgres.useExternalSecret=true` and configure `postgres.externalSecret.secretStoreRef`, `remoteRef.secretName` (e.g. Tofu output `aws_secretsmanager_secret_name`), and `targetSecretName`.
3. When using external Postgres (RDS), set `api.existingSecret` and `celeryWorker.existingSecret` to the name of a Secret created by ESO that contains `DATABASE_URL` and `CELERY_BROKER_URL`.

Do not put production passwords in `values.yaml`; use ESO and Tofu-generated secrets.

## Values reference

| Value | Description |
|-------|-------------|
| `redis.enabled` | Deploy in-cluster Redis (default: true). If false, set `redis.externalHost` or broker URL via env. |
| `postgres.enabled` | Deploy in-cluster Postgres (default: true). If false, set `postgres.externalUrl`. |
| `postgres.useExternalSecret` | When true, use ESO to sync Postgres password from AWS Secrets Manager; do not create inline Secret. |
| `keda.enabled` | Create KEDA ScaledObject for celery-worker (default: true). Requires KEDA installed. |
| `api.shortServiceName` | Create Service named `api` for frontend (default: false). Set true when one release per namespace. |
| `api.hpa.enabled` / `frontend.hpa.enabled` | Enable HPA for API/frontend (default: false). |
| `api.pdb.enabled` / `frontend.pdb.enabled` | Enable PDB for API/frontend (default: false). |
| `networkPolicy.enabled` | Enable default-deny + allow policies (default: false). Requires CNI support. |
| `replicaCount.celeryWorker.min/max` | KEDA min/max replicas for celery-worker. |
