"""
Kubernetes (EKS) job adapter: submit heavy workloads as K8s Jobs when configured.
Set QASIC_EKS_IMAGE (e.g. qasic-fdtd:latest) and optionally QASIC_EKS_NAMESPACE to enable.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from src.backend.adapters.base import ComputeAdapter
from src.backend.task_registry import BACKEND_AWS_EKS


def _submit_kubernetes_job(
    task_type: str,
    config: dict[str, Any],
    inputs: dict[str, Any],
    work_dir: Path,
) -> tuple[dict[str, Any], str | None]:
    """Submit a Kubernetes Job and poll until completion. Returns (outputs, error)."""
    image = os.environ.get("QASIC_EKS_IMAGE", "").strip()
    if not image:
        return {}, "EKS backend not configured (set QASIC_EKS_IMAGE)"
    namespace = os.environ.get("QASIC_EKS_NAMESPACE", "default").strip()
    try:
        from kubernetes import client, config as k8s_config
    except ImportError:
        return {}, "EKS backend requires kubernetes package (pip install kubernetes)"
    try:
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()
    except Exception as e:
        return {}, f"Kubernetes config failed: {e}"
    job_name = f"qasic-{task_type}-{int(time.time())}"
    batch = client.BatchV1Api()
    # Command: image must run the task and write outputs to artifact store; placeholder exits 0 for demo
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name=job_name, namespace=namespace),
        spec=client.V1JobSpec(
            ttl_seconds_after_finished=300,
            template=client.V1PodTemplateSpec(
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    containers=[
                        client.V1Container(
                            name="worker",
                            image=image,
                            command=["python", "-c", "import time; time.sleep(1)"],
                            env=[client.V1EnvVar(name="TASK_TYPE", value=task_type)],
                        )
                    ],
                )
            ),
        ),
    )
    try:
        batch.create_namespaced_job(namespace=namespace, body=job)
    except Exception as e:
        return {}, f"Failed to create Job: {e}"
    # Poll for completion (simplified; in production use watch or async)
    for _ in range(600):
        j = batch.read_namespaced_job(name=job_name, namespace=namespace)
        if j.status.succeeded and j.status.succeeded >= 1:
            break
        if j.status.failed and j.status.failed >= 1:
            return {}, "Kubernetes Job failed"
        time.sleep(2)
    else:
        return {}, "Kubernetes Job timed out"
    # Job succeeded; in production the job would write outputs to artifact store and we would fetch them
    return {"job_name": job_name, "namespace": namespace}, None


class KubernetesJobAdapter(ComputeAdapter):
    """Execute tasks by submitting Kubernetes Jobs (EKS). Requires QASIC_EKS_IMAGE and kubernetes package."""

    def supports(self, task_type: str, backend: str) -> bool:
        return backend == BACKEND_AWS_EKS

    def execute(
        self,
        task_type: str,
        config: dict[str, Any],
        inputs: dict[str, Any],
        work_dir: Path,
    ) -> tuple[dict[str, Any], str | None]:
        return _submit_kubernetes_job(task_type, config, inputs, work_dir)
