"""
Celery tasks for heavy workloads: pipeline, MEEP unit-cell sweep, inverse design (GNN).
Keeps API/frontend responsive by offloading to workers.
Emits progress to Redis Pub/Sub (channel qasic:task:{task_id}:log) for real-time UI when CELERY_BROKER_URL is set.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ENGINEERING_DIR = REPO_ROOT / "src" / "core_compute" / "engineering"

TASK_LOG_CHANNEL_PREFIX = "qasic:task:"


def _run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 3600) -> tuple[int, str, str]:
    r = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def _publish_progress(task_id: str | None, message: str, step: str | None = None, done: bool = False):
    """Publish progress to Redis for SSE streaming. No-op if Redis not available."""
    if not task_id:
        return
    try:
        import redis
        broker = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
        r = redis.from_url(broker)
        payload = {"message": message, "step": step, "done": done}
        r.publish(f"{TASK_LOG_CHANNEL_PREFIX}{task_id}:log", json.dumps(payload))
    except Exception:
        pass


def _task_app():
    from src.backend.celery_app import get_celery_app
    return get_celery_app()


app = _task_app()


@app.task(bind=True, name="qasic.run_pipeline")
def run_pipeline_task(self, output_base: str = "pipeline_result", fast: bool = False,
                     routing_method: str = "qaoa", model: str = "mlp", heac: bool = False,
                     skip_routing: bool = False, skip_inverse: bool = False,
                     hardware: bool = False):
    """Run full pipeline (routing + inverse + optional HEaC). Publishes progress to Redis for real-time UI."""
    task_id = self.request.id if getattr(self.request, "id", None) else None
    _publish_progress(task_id, "Starting pipeline", step="pipeline", done=False)

    # Option A: single run_pipeline.py (simpler; progress only at start/end unless we parse output)
    cmd = [sys.executable, str(ENGINEERING_DIR / "run_pipeline.py"), "-o", output_base]
    if fast:
        cmd.append("--fast")
    if routing_method in ("qaoa", "rl"):
        cmd.extend(["--routing-method", routing_method])
    if model in ("mlp", "gnn"):
        cmd.extend(["--model", model])
    if heac:
        cmd.append("--heac")
    if skip_routing:
        cmd.append("--skip-routing")
    if skip_inverse:
        cmd.append("--skip-inverse")
    if hardware:
        cmd.append("--hardware")

    _publish_progress(task_id, "Running routing and inverse design…", step="routing", done=False)
    _publish_progress(task_id, "Running inverse design…", step="inverse_design", done=False)
    code, out, err = _run_cmd(cmd, timeout=1800)
    routing_json = ENGINEERING_DIR / f"{output_base}_routing.json"
    inverse_json = ENGINEERING_DIR / f"{output_base}_inverse.json"
    gds_path = ENGINEERING_DIR / f"{output_base}.gds"

    if code != 0:
        _publish_progress(task_id, f"Pipeline failed: {err or out}", step="inverse_design", done=True)
        try:
            from storage.db import update_pipeline_run
            update_pipeline_run(task_id=task_id, status="failed", error_message=err or out)
        except Exception:
            pass
        return {"success": False, "exit_code": code, "stderr": err, "stdout": out}
    _publish_progress(task_id, "Pipeline completed", step="manifest_to_gds", done=True)
    try:
        from storage.db import update_pipeline_run
        update_pipeline_run(
            task_id=task_id,
            status="success",
            routing_path=str(routing_json) if routing_json.exists() else None,
            inverse_path=str(inverse_json) if inverse_json.exists() else None,
            gds_path=str(gds_path) if gds_path.exists() else None,
        )
    except Exception:
        pass
    result = {"success": True, "output_base": output_base}
    if routing_json.exists():
        try:
            with open(routing_json, encoding="utf-8") as f:
                result["routing"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    if inverse_json.exists():
        try:
            with open(inverse_json, encoding="utf-8") as f:
                result["inverse"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return result


def _circuit_to_asic_result_serializable(raw: dict) -> dict:
    """Build a JSON-serializable result from run_qasm_to_asic output (drop _topology, _interaction_graph; add nodes/edges)."""
    out = {k: v for k, v in raw.items() if not k.startswith("_")}
    out["geometry_manifest_path"] = raw.get("_geometry_manifest_path")
    out["custom_asic_manifest_path"] = raw.get("_custom_asic_manifest_path")
    graph = raw.get("_interaction_graph")
    if graph is not None:
        try:
            import networkx as nx
            out["nodes"] = list(nx.nodes(graph))
            out["edges"] = [list(e) for e in nx.edges(graph)]
        except Exception:
            pass
    return out


@app.task(bind=True, name="qasic.circuit_to_asic")
def circuit_to_asic_task(self, qasm_string: str, circuit_name: str | None = None, output_subdir: str | None = None):
    """Run qasm_to_asic (Algorithm-to-ASIC) on QASM string. Returns serializable result for API."""
    task_id = self.request.id if getattr(self.request, "id", None) else None
    _publish_progress(task_id, "Starting circuit-to-ASIC", step="circuit_to_asic", done=False)
    try:
        from src.core_compute.engineering.qasm_to_asic_pipeline import run_qasm_to_asic
    except ImportError:
        _publish_progress(task_id, "Import error: qasm_to_asic not available", step="circuit_to_asic", done=True)
        return {"success": False, "error": "qasm_to_asic pipeline not available"}
    output_dir = output_subdir or str(ENGINEERING_DIR / "circuit_runs" / (task_id or "sync"))
    os.makedirs(output_dir, exist_ok=True)
    try:
        raw = run_qasm_to_asic(
            qasm_string=qasm_string,
            output_dir=output_dir,
            circuit_name=circuit_name or "circuit",
        )
        _publish_progress(task_id, "Circuit-to-ASIC completed", step="circuit_to_asic", done=True)
        return {"success": True, "circuit_to_asic": _circuit_to_asic_result_serializable(raw)}
    except Exception as e:
        _publish_progress(task_id, str(e), step="circuit_to_asic", done=True)
        return {"success": False, "error": str(e)}


def _routing_from_circuit_graph(graph, fast: bool = False, hardware: bool = False) -> dict:
    """Run routing QUBO in-process using circuit-derived interaction graph. Returns routing result dict (mapping, solver, etc.)."""
    import numpy as np
    from src.core_compute.asic.topology_builder import edges_to_interaction_matrix
    from src.core_compute.engineering.routing_qubo_qaoa import (
        build_routing_qubo,
        solve_routing,
        interpret_routing,
    )
    from datetime import datetime, timezone
    nodes = sorted(graph.nodes())
    n = len(nodes)
    if n == 0:
        return {"num_logical_qubits": 0, "num_physical_nodes": 0, "topology": "custom", "mapping": []}
    node_to_idx = {q: i for i, q in enumerate(nodes)}
    edges = [(node_to_idx[u], node_to_idx[v]) for u, v in graph.edges()]
    interaction_matrix = edges_to_interaction_matrix(edges, n)
    qp = build_routing_qubo(num_logical_qubits=n, num_physical_nodes=n, interaction_matrix=interaction_matrix)
    maxiter = 20 if fast else 100
    reps = 1 if fast else 2
    result = solve_routing(qp, use_qaoa=True, qaoa_reps=reps, optimizer_maxiter=maxiter)
    x_vals = result.get("x")
    mapping = []
    if x_vals is not None:
        x_vals = np.asarray(x_vals).ravel()
        mapping = interpret_routing(x_vals, n, n)
    return {
        "num_logical_qubits": n,
        "num_physical_nodes": n,
        "topology": "custom",
        "solver": result.get("solver", "unknown"),
        "objective_value": float(result["fval"]) if result.get("fval") is not None else None,
        "backend": None,
        "mapping": [{"logical": a, "physical": b} for a, b in mapping],
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@app.task(bind=True, name="qasic.run_pipeline_with_circuit")
def run_pipeline_with_circuit_task(
    self,
    qasm_string: str,
    circuit_name: str = "circuit",
    output_base: str = "pipeline_result",
    fast: bool = False,
    routing_method: str = "qaoa",
    model: str = "mlp",
    heac: bool = False,
    hardware: bool = False,
    run_id: int | None = None,
):
    """Run qasm_to_asic then routing (circuit-derived) then run_pipeline.py --skip-routing (inverse + optional HEaC). Loads credentials from vault into env. If run_id is set, updates DAG run status on completion."""
    task_id = self.request.id if getattr(self.request, "id", None) else None
    try:
        from config import get_app_config
        from src.backend.credentials_vault import load_credentials_into_env
        cfg = get_app_config()
        creds_path = getattr(cfg.paths, "credentials_file", None) or ""
        load_credentials_into_env(creds_path, REPO_ROOT)
    except Exception:
        pass
    _publish_progress(task_id, "Starting pipeline with circuit", step="pipeline", done=False)
    try:
        from src.core_compute.engineering.qasm_to_asic_pipeline import run_qasm_to_asic
    except ImportError:
        _publish_progress(task_id, "qasm_to_asic not available", step="pipeline", done=True)
        return {"success": False, "error": "qasm_to_asic pipeline not available"}
    output_dir = str(ENGINEERING_DIR / "circuit_runs" / (task_id or "sync"))
    os.makedirs(output_dir, exist_ok=True)
    try:
        raw = run_qasm_to_asic(
            qasm_string=qasm_string,
            output_dir=output_dir,
            circuit_name=circuit_name,
        )
    except Exception as e:
        _publish_progress(task_id, str(e), step="pipeline", done=True)
        if run_id is not None:
            try:
                from storage.db import update_dag_run
                update_dag_run(run_id, status="failed", error_message=str(e))
            except Exception:
                pass
        return {"success": False, "error": str(e)}
    graph = raw.get("_interaction_graph")
    if graph is None or graph.number_of_nodes() == 0:
        _publish_progress(task_id, "No interaction graph from circuit", step="pipeline", done=True)
        return {"success": True, "circuit_to_asic": _circuit_to_asic_result_serializable(raw), "pipeline": None}
    _publish_progress(task_id, "Running routing (circuit-derived topology)", step="routing", done=False)
    routing_result = _routing_from_circuit_graph(graph, fast=fast, hardware=hardware)
    routing_json = ENGINEERING_DIR / f"{output_base}_routing.json"
    with open(routing_json, "w", encoding="utf-8") as f:
        json.dump(routing_result, f, indent=2)
    _publish_progress(task_id, "Routing done; running inverse design and pipeline", step="inverse_design", done=False)
    _publish_progress(task_id, "Running inverse design and pipeline", step="manifest_to_gds", done=False)
    cmd = [sys.executable, str(ENGINEERING_DIR / "run_pipeline.py"), "-o", output_base, "--skip-routing"]
    if fast:
        cmd.append("--fast")
    if model in ("mlp", "gnn"):
        cmd.extend(["--model", model])
    if heac:
        cmd.append("--heac")
    if hardware:
        cmd.append("--hardware")
    code, out, err = _run_cmd(cmd, timeout=1800)
    if code != 0:
        _publish_progress(task_id, f"Pipeline failed: {err or out}", step="manifest_to_gds", done=True)
        if run_id is not None:
            try:
                from storage.db import update_dag_run
                update_dag_run(run_id, status="failed", error_message=err or out)
            except Exception:
                pass
        try:
            from storage.db import update_pipeline_run
            update_pipeline_run(task_id=task_id, status="failed", error_message=err or out)
        except Exception:
            pass
        return {"success": False, "exit_code": code, "stderr": err, "stdout": out, "circuit_to_asic": _circuit_to_asic_result_serializable(raw)}
    _publish_progress(task_id, "Pipeline completed", step="manifest_to_gds", done=True)
    if run_id is not None:
        try:
            from storage.db import update_dag_run
            update_dag_run(run_id, status="success")
        except Exception:
            pass
    try:
        from storage.db import update_pipeline_run
        update_pipeline_run(
            task_id=task_id,
            status="success",
            routing_path=str(routing_json) if routing_json.exists() else None,
            inverse_path=str(ENGINEERING_DIR / f"{output_base}_inverse.json") if (ENGINEERING_DIR / f"{output_base}_inverse.json").exists() else None,
            gds_path=str(ENGINEERING_DIR / f"{output_base}.gds") if (ENGINEERING_DIR / f"{output_base}.gds").exists() else None,
        )
    except Exception:
        pass
    result = {"success": True, "output_base": output_base, "circuit_to_asic": _circuit_to_asic_result_serializable(raw)}
    inv_path = ENGINEERING_DIR / f"{output_base}_inverse.json"
    if inv_path.exists():
        try:
            with open(inv_path, encoding="utf-8") as f:
                result["inverse"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    result["routing"] = routing_result
    return result


@app.task(bind=True, name="qasic.run_dag")
def run_dag_task(self, run_id: int):
    """Execute a DAG run (Celery canvas for parallel waves, or sequential fallback)."""
    task_id = self.request.id if getattr(self.request, "id", None) else None
    _publish_progress(task_id, f"Starting DAG run {run_id}", step="dag", done=False)
    try:
        from src.backend.executor import run_dag
        result = run_dag(run_id, celery_task_id=task_id, run_dag_node_task=run_dag_node_task)
        if result.get("success"):
            _publish_progress(task_id, "DAG run completed", step="dag", done=True)
            return result
        _publish_progress(task_id, result.get("error", "Failed"), step="dag", done=True)
        return result
    except Exception as e:
        _publish_progress(task_id, str(e), step="dag", done=True)
        raise


@app.task(bind=True, name="qasic.run_dag_node")
def run_dag_node_task(self, a, b, c=None):
    """
    Run a single DAG node. Called by the DAG compiler canvas.
    Signature: (run_id, node_id) when first in chain, else (prev_results, run_id, node_id).
    Reads node_outputs from DB (completed upstream nodes), dispatches, writes outputs to DB.
    """
    if c is None:
        run_id, node_id = int(a), str(b)
    else:
        run_id, node_id = int(b), str(c)
    from datetime import datetime, timezone
    from pathlib import Path
    import tempfile
    from storage.db import get_dag_run, update_dag_run, upsert_dag_run_node, is_enabled
    from src.backend.executor import _get_node_by_id, _get_inputs_for_node
    from src.backend.dispatcher import dispatch as dispatcher_dispatch
    from src.backend.task_registry import get_task_type

    if not is_enabled():
        raise RuntimeError("Database not configured")
    run = get_dag_run(run_id)
    if not run:
        raise RuntimeError("Run not found")
    nodes = run.get("nodes_snapshot") or []
    edges = run.get("edges_snapshot") or []
    node_outputs = {}
    for ns in run.get("nodes") or []:
        if ns.get("status") == "success" and ns.get("outputs"):
            node_outputs[ns["node_id"]] = ns["outputs"]
    node = _get_node_by_id(nodes, node_id)
    if not node:
        upsert_dag_run_node(run_id, node_id, status="failed", error_message="Node not found")
        update_dag_run(run_id, status="failed", error_message="Node not found")
        raise RuntimeError("Node not found")
    data = node.get("data") or {}
    config = data.get("config") or {}
    task_type = data.get("task_type")
    if not task_type:
        upsert_dag_run_node(run_id, node_id, status="failed", error_message="Missing task_type")
        update_dag_run(run_id, status="failed", error_message="Missing task_type")
        raise RuntimeError("Missing task_type")
    if not get_task_type(task_type):
        upsert_dag_run_node(run_id, node_id, status="failed", error_message=f"Unknown task_type: {task_type}")
        update_dag_run(run_id, status="failed", error_message=f"Unknown task_type: {task_type}")
        raise RuntimeError(f"Unknown task_type: {task_type}")
    inputs = _get_inputs_for_node(node_id, nodes, edges, node_outputs)
    # Resolve URI inputs to local paths for this worker
    try:
        from src.backend.artifact_store import resolve_input_to_path
        inputs = {k: str(resolve_input_to_path(v)) if isinstance(v, str) and (v.startswith("file://") or v.startswith("s3://")) else v for k, v in inputs.items()}
    except Exception:
        pass
    now = datetime.now(timezone.utc)
    upsert_dag_run_node(run_id, node_id, status="running", started_at=now)
    work_dir = Path(tempfile.mkdtemp(prefix="qasic_dag_"))
    try:
        outputs, err = dispatcher_dispatch(task_type, config, inputs, work_dir)
        if err:
            upsert_dag_run_node(
                run_id, node_id,
                status="failed",
                finished_at=datetime.now(timezone.utc),
                error_message=err,
            )
            update_dag_run(run_id, status="failed", finished_at=datetime.now(timezone.utc), error_message=f"Node {node_id}: {err}")
            raise RuntimeError(err)
        # Store file outputs as URIs for cross-worker use
        try:
            from src.backend.artifact_store import store_outputs_as_uris
            outputs = store_outputs_as_uris(run_id, outputs)
        except Exception:
            pass
        upsert_dag_run_node(
            run_id, node_id,
            status="success",
            finished_at=datetime.now(timezone.utc),
            outputs=outputs,
        )
        return (node_id, outputs)
    finally:
        try:
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


@app.task(name="qasic.sweep_stale_dag_runs")
def sweep_stale_dag_runs_task(interval_seconds: int = 60) -> int:
    """Mark DAG runs as failed when status=running and no heartbeat in interval_seconds. For Celery beat."""
    try:
        from storage.db import sweep_stale_dag_runs
        return sweep_stale_dag_runs(interval_seconds=interval_seconds)
    except Exception:
        return 0


@app.task(bind=True, name="qasic.meep_sweep")
def meep_sweep_task(self, output_path: str | None = None, points: int = 21, no_meep: bool = False):
    """Run MEEP unit-cell sweep (meta-atom library)."""
    out = output_path or str(ENGINEERING_DIR / "meta_atom_library.json")
    cmd = [sys.executable, str(ENGINEERING_DIR / "heac" / "meep_unit_cell_sweep.py"),
           "-o", out, "--points", str(points)]
    if no_meep:
        cmd.append("--no-meep")
    code, stdout, stderr = _run_cmd(cmd, timeout=1200)
    if code != 0:
        return {"success": False, "exit_code": code, "stderr": stderr}
    result = {"success": True, "output_path": out}
    if os.path.isfile(out):
        try:
            with open(out, encoding="utf-8") as f:
                data = json.load(f)
            result["library_preview"] = list(data.keys()) if isinstance(data, dict) else []
        except Exception:
            pass
    return result


def _run_inverse_design_inprocess(
    routing_result_path: str | None,
    model: str,
    device: str,
    output_path: str,
    phase_band: str | None,
) -> dict | None:
    """Call engineering inverse design in-process when available. Returns result dict or None on import error."""
    try:
        from src.core_compute.engineering.metasurface_inverse_net import run_inverse_design
    except ImportError:
        try:
            sys.path.insert(0, str(REPO_ROOT))
            from src.core_compute.engineering.metasurface_inverse_net import run_inverse_design
        except ImportError:
            return None
    return run_inverse_design(
        routing_result_path=routing_result_path,
        output_path=output_path,
        device=device,
        model=model,
        phase_band_str=phase_band,
    )


@app.task(bind=True, name="qasic.inverse_design")
def inverse_design_task(self, routing_result_path: str | None = None, model: str = "mlp",
                        device: str = "auto", output_base: str = "pipeline_result",
                        phase_band: str | None = None):
    """Run inverse design (MLP or GNN). Prefers in-process run_inverse_design; falls back to subprocess."""
    out_json = str(ENGINEERING_DIR / f"{output_base}_inverse.json")
    inv = _run_inverse_design_inprocess(
        routing_result_path=routing_result_path,
        model=model,
        device=device,
        output_path=out_json,
        phase_band=phase_band,
    )
    if inv is not None:
        result = {"success": True, "output_json": out_json, "inverse": inv}
        return result
    cmd = [sys.executable, str(ENGINEERING_DIR / "metasurface_inverse_net.py"),
           "-o", out_json, "--model", model, "--device", device]
    if routing_result_path and os.path.isfile(routing_result_path):
        cmd.extend(["--routing-result", routing_result_path])
    if phase_band:
        cmd.extend(["--phase-band", phase_band])
    code, stdout, stderr = _run_cmd(cmd, timeout=600)
    if code != 0:
        return {"success": False, "exit_code": code, "stderr": stderr}
    result = {"success": True, "output_json": out_json}
    if os.path.isfile(out_json):
        try:
            with open(out_json, encoding="utf-8") as f:
                result["inverse"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return result
