"""
Prefect 2 flow: DAG for the metasurface pipeline. Retry only failed nodes.
Run: prefect flow run pipeline_flow -p pipeline_params.json
Or: python -m orchestration.pipeline_flow (with params in code or env).
"""
from __future__ import annotations

import os
from typing import Any

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner

from .pipeline_params import PipelineParams
from . import pipeline_tasks as tasks


def _default_params(script_dir: str, repo_root: str) -> PipelineParams:
    return PipelineParams(
        repo_root=repo_root,
        script_dir=script_dir,
    )


# --- Tasks (each retriable independently) ---

@task(name="routing", retries=2, retry_delay_seconds=30)
def run_routing(params: PipelineParams) -> str:
    tasks.set_repo_root(params.repo_root)
    return tasks.task_routing(params)


@task(name="superscreen", retries=1, retry_delay_seconds=10)
def run_superscreen(params: PipelineParams, routing_json: str) -> str | None:
    tasks.set_repo_root(params.repo_root)
    return tasks.task_superscreen(params, routing_json)


@task(name="inverse_design", retries=2, retry_delay_seconds=60)
def run_inverse_design(params: PipelineParams, routing_json: str) -> tuple[str, str]:
    tasks.set_repo_root(params.repo_root)
    return tasks.task_inverse_design(params, routing_json)


@task(name="heac_library", retries=2, retry_delay_seconds=60)
def run_heac_library(params: PipelineParams) -> str | None:
    tasks.set_repo_root(params.repo_root)
    return tasks.task_heac_library(params)


@task(name="heac_phases_to_geometry", retries=2, retry_delay_seconds=30)
def run_heac_phases_to_geometry(
    params: PipelineParams, routing_json: str, npy_path: str, heac_library: str | None
) -> str | None:
    tasks.set_repo_root(params.repo_root)
    return tasks.task_heac_phases_to_geometry(params, routing_json, npy_path, heac_library)


@task(name="manifest_to_gds", retries=2, retry_delay_seconds=20)
def run_manifest_to_gds(params: PipelineParams, manifest_path: str | None) -> str | None:
    tasks.set_repo_root(params.repo_root)
    return tasks.task_manifest_to_gds(params, manifest_path)


@task(name="drc", retries=1, retry_delay_seconds=15)
def run_drc(params: PipelineParams, gds_path: str | None) -> str | None:
    tasks.set_repo_root(params.repo_root)
    return tasks.task_drc(params, gds_path)


@task(name="lvs", retries=1, retry_delay_seconds=15)
def run_lvs(
    params: PipelineParams, manifest_path: str | None, gds_path: str | None, routing_json: str
) -> str | None:
    tasks.set_repo_root(params.repo_root)
    return tasks.task_lvs(params, manifest_path, gds_path, routing_json)


@task(name="dft", retries=1, retry_delay_seconds=15)
def run_dft(
    params: PipelineParams, manifest_path: str | None, gds_path: str | None
) -> str | None:
    tasks.set_repo_root(params.repo_root)
    return tasks.task_dft(params, manifest_path, gds_path)


@task(name="thermal", retries=1, retry_delay_seconds=10)
def run_thermal(
    params: PipelineParams, routing_json: str, npy_path: str | None
) -> str | None:
    tasks.set_repo_root(params.repo_root)
    return tasks.task_thermal(params, routing_json, npy_path)


@task(name="meep_verify", retries=1, retry_delay_seconds=20)
def run_meep_verify(params: PipelineParams, manifest_path: str | None) -> str | None:
    tasks.set_repo_root(params.repo_root)
    return tasks.task_meep_verify(params, manifest_path)


@task(name="packaging", retries=1, retry_delay_seconds=10)
def run_packaging(params: PipelineParams, manifest_path: str | None) -> str | None:
    tasks.set_repo_root(params.repo_root)
    return tasks.task_packaging(params, manifest_path)


@task(name="parasitic", retries=1, retry_delay_seconds=10)
def run_parasitic(
    params: PipelineParams, manifest_path: str | None, routing_json: str
) -> str | None:
    tasks.set_repo_root(params.repo_root)
    return tasks.task_parasitic(params, manifest_path, routing_json)


@flow(
    name="qasic-pipeline",
    description="Metasurface pipeline: routing -> inverse -> HEaC -> GDS -> DRC/LVS/DFT/thermal/MEEP/parasitic",
    task_runner=ConcurrentTaskRunner(),
)
def pipeline_flow(params: PipelineParams | None = None) -> dict[str, Any]:
    """
    Run the full pipeline as a DAG. Each step is a Prefect task with retries.
    Pass PipelineParams; if None, uses defaults with script_dir/repo_root from this file.
    """
    # orchestration/ is at repo root; pipeline scripts live in engineering/
    orchestration_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(orchestration_dir)
    script_dir = os.path.join(repo_root, "engineering")
    if params is None:
        params = _default_params(script_dir, repo_root)
    else:
        params.repo_root = params.repo_root or repo_root
        params.script_dir = params.script_dir or script_dir

    # --- Linear chain: routing -> inverse ---
    routing_json = run_routing(params)
    run_superscreen(params, routing_json)  # optional, no downstream deps

    inverse_json, npy_path = run_inverse_design(params, routing_json)

    # --- HEaC branch (can run in parallel with thermal later) ---
    heac_library = run_heac_library(params) if params.heac else None
    manifest_path = run_heac_phases_to_geometry(params, routing_json, npy_path, heac_library)

    # --- GDS chain (manifest -> gds -> drc/lvs/dft) ---
    gds_path = run_manifest_to_gds(params, manifest_path)
    if gds_path:
        run_drc(params, gds_path)
        run_lvs(params, manifest_path, gds_path, routing_json)
        run_dft(params, manifest_path, gds_path)

    # --- Optional steps that only need routing/inverse or manifest ---
    run_thermal(params, routing_json, npy_path)
    run_meep_verify(params, manifest_path)
    run_packaging(params, manifest_path)
    run_parasitic(params, manifest_path, routing_json)

    return {
        "routing_json": routing_json,
        "inverse_json": inverse_json,
        "npy_path": npy_path,
        "manifest_path": manifest_path,
        "gds_path": gds_path if (params.gds or params.drc or params.lvs) else None,
    }
