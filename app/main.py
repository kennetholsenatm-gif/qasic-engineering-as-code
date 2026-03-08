"""
FastAPI backend for QASIC Engineering-as-Code.
Provides API routes to run protocol, routing, pipeline, inverse design,
quantum illumination, quantum radar; return latest results and doc links.
Run with: uvicorn app.main:app --reload
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# In-memory store for async IBM protocol jobs: job_id -> {job, backend, protocol}
_ibm_job_store: dict[str, dict] = {}

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ENGINEERING_DIR = REPO_ROOT / "engineering"
DOCS_DIR = REPO_ROOT / "docs"
PIPELINE_BASE = "pipeline_result"
ROUTING_JSON = ENGINEERING_DIR / f"{PIPELINE_BASE}_routing.json"
INVERSE_JSON = ENGINEERING_DIR / f"{PIPELINE_BASE}_inverse.json"

# CORS: use BACKEND_CORS_ORIGINS (comma-separated) in production; default "*" for dev
_cors_origins = os.environ.get("BACKEND_CORS_ORIGINS", "*").strip()
if _cors_origins == "*":
    _allow_origins = ["*"]
else:
    _allow_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()] or ["*"]

app = FastAPI(title="QASIC Engineering-as-Code API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    """Run command; return (exit_code, stderr_or_stdout)."""
    r = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
    )
    err = (r.stderr or "").strip() or (r.stdout or "").strip()
    return r.returncode, err


# --- Request bodies ---
class RunProtocolRequest(BaseModel):
    protocol: str = "teleport"
    backend: str = "sim"


class RunRoutingRequest(BaseModel):
    backend: str = "sim"
    fast: bool = False
    topology: str | None = None  # linear_chain | star | repeater_chain
    qubits: int | None = None
    hub: int | None = None  # for star
    routing_method: str | None = None  # qaoa (default) | rl


class RunPipelineRequest(BaseModel):
    backend: str = "sim"
    fast: bool = False
    routing_method: str | None = None  # qaoa (default) | rl
    model: str | None = None  # mlp (default) | gnn
    heac: bool = False
    skip_routing: bool = False
    skip_inverse: bool = False


class RunInverseRequest(BaseModel):
    phase_band: str | None = None
    routing_result_path: str | None = None


class QuantumIlluminationRequest(BaseModel):
    eta: float = 0.1


class QuantumRadarRequest(BaseModel):
    eta: float = 0.1
    n_b: float = 10.0
    r: float = 0.5


class QuantumRadarSweepRequest(BaseModel):
    param: str = "r"  # eta | n_b | r
    min_val: float | None = None
    max_val: float | None = None
    steps: int = 21
    eta: float = 0.2
    n_b: float = 2.0
    r: float = 0.5


class QuantumRadarOptimizeRequest(BaseModel):
    param: str = "r"
    optimize_min: float | None = None
    optimize_max: float | None = None
    steps: int = 50
    eta: float = 0.2
    n_b: float = 2.0
    r: float = 0.5
    maximize: str = "mutual_info"  # mutual_info | snr


class RunQKDRequest(BaseModel):
    protocol: str = "bb84"  # bb84 | e91
    n_bits: int = 64  # for BB84
    n_trials: int = 500  # for E91
    seed: int | None = None


class QRNCMintRequest(BaseModel):
    num_bytes: int = 32
    use_real_hardware: bool = False
    ibm_token: str | None = None
    token_id: str | None = None


class QRNCExchangeRequest(BaseModel):
    token_a_hex: str
    token_b_hex: str
    party_a_id: str = "Alice"
    party_b_id: str = "Bob"


class BQTCRunCycleRequest(BaseModel):
    dry_run: bool = True  # BQTC pipeline.yaml actuator.dry_run is separate; this is for API docs


@app.post("/api/apps/qrnc/mint")
def apps_qrnc_mint(req: QRNCMintRequest):
    """Mint a quantum-backed QRNC token (sim or IBM hardware)."""
    try:
        from apps.qrnc import mint_qrnc
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"QRNC import failed: {e}")
    try:
        token = mint_qrnc(
            num_bytes=req.num_bytes,
            use_real_hardware=req.use_real_hardware,
            ibm_token=req.ibm_token,
            token_id=req.token_id,
        )
        return {
            "value": token.value,
            "id": token.id,
            "issued_at": token.issued_at.isoformat() if token.issued_at else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/apps/qrnc/exchange")
def apps_qrnc_exchange(req: QRNCExchangeRequest):
    """Run two-party QRNC exchange (commit-then-reveal). Returns received tokens and record."""
    try:
        from apps.qrnc import QRNC, run_two_party_exchange
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"QRNC import failed: {e}")
    try:
        token_a = QRNC.from_hex(req.token_a_hex)
        token_b = QRNC.from_hex(req.token_b_hex)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid token hex: {e}")
    try:
        received_by_a, received_by_b, record = run_two_party_exchange(
            token_a, token_b, party_a_id=req.party_a_id, party_b_id=req.party_b_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if received_by_a is None:
        return {"success": False, "message": "Verification failed"}
    return {
        "success": True,
        "received_by_a_hex": received_by_a.value,
        "received_by_b_hex": received_by_b.value,
        "record": {
            "party_a_id": record.party_a_id,
            "party_b_id": record.party_b_id,
            "timestamp": record.timestamp.isoformat(),
        },
    }


@app.post("/api/apps/bqtc/run-cycle")
def apps_bqtc_run_cycle(req: BQTCRunCycleRequest):
    """Run one BQTC pipeline cycle (no live telemetry; buffer may be empty)."""
    bqtc_dir = REPO_ROOT / "apps" / "bqtc"
    script = bqtc_dir / "run_one_cycle.py"
    if not script.is_file():
        raise HTTPException(status_code=503, detail="BQTC run_one_cycle.py not found")
    cmd = [sys.executable, str(script)]
    code, out = _run(cmd, cwd=bqtc_dir)
    if code != 0:
        raise HTTPException(status_code=503, detail=out or "BQTC run-one-cycle failed")
    try:
        data = json.loads(out) if out.strip() else []
        return {"results": data}
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid BQTC output: {e}")


@app.post("/api/run/qkd")
def run_qkd(req: RunQKDRequest):
    """Run pedagogical QKD (BB84 or E91) in simulation."""
    if req.protocol.lower() == "bb84":
        result = _run_bb84(n_bits=req.n_bits, seed=req.seed)
    elif req.protocol.lower() == "e91":
        result = _run_e91(n_trials=req.n_trials, seed=req.seed)
    else:
        raise HTTPException(status_code=400, detail="protocol must be bb84 or e91")
    return result


def _run_bb84(n_bits: int, seed: int | None) -> dict:
    from protocols.qkd import run_bb84
    return run_bb84(n_bits=n_bits, seed=seed)


def _run_e91(n_trials: int, seed: int | None) -> dict:
    from protocols.qkd import run_e91
    return run_e91(n_trials=n_trials, seed=seed)


@app.post("/api/run/protocol")
def run_protocol(req: RunProtocolRequest):
    """Run ASIC protocol on sim (blocking) or IBM hardware (returns job_id for WebSocket polling)."""
    use_hardware = req.backend.lower() == "hardware"
    if use_hardware:
        try:
            from engineering.run_protocol_on_ibm import submit_protocol_job, get_job_status_and_result
            job_id, job, backend_name = submit_protocol_job(req.protocol, shots=1024)
            _ibm_job_store[job_id] = {"job": job, "backend": backend_name, "protocol": req.protocol}
            return {"job_id": job_id, "status": "submitted", "backend": backend_name}
        except Exception as e:
            raise HTTPException(status_code=503, detail=str(e))
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    try:
        cmd = [
            sys.executable,
            str(ENGINEERING_DIR / "run_protocol_on_ibm.py"),
            "--protocol", req.protocol,
            "-o", out_path,
        ]
        code, err = _run(cmd)
        if code != 0:
            raise HTTPException(status_code=503, detail=err or "Protocol run failed")
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Script or output not found: {e}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid output JSON: {e}")
    finally:
        if os.path.isfile(out_path):
            try:
                os.unlink(out_path)
            except OSError:
                pass


@app.websocket("/ws/job/{job_id}")
async def websocket_job_status(websocket: WebSocket, job_id: str):
    """Stream IBM job status (QUEUED, RUNNING, DONE, ERROR) until completion."""
    await websocket.accept()
    if job_id not in _ibm_job_store:
        await websocket.send_json({"status": "ERROR", "error": "Unknown job_id"})
        await websocket.close()
        return
    from engineering.run_protocol_on_ibm import get_job_status_and_result
    entry = _ibm_job_store[job_id]
    job = entry["job"]
    try:
        while True:
            status_str, result_dict = get_job_status_and_result(job)
            await websocket.send_json({"status": status_str, "result": result_dict})
            if status_str in ("DONE", "ERROR"):
                break
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()


@app.post("/api/run/routing")
def run_routing(req: RunRoutingRequest):
    """Run QUBO routing (QAOA or RL) on sim or IBM hardware."""
    use_hardware = req.backend.lower() == "hardware"
    use_rl = (req.routing_method or "qaoa").lower() == "rl"
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    try:
        if use_rl:
            cmd = [
                sys.executable,
                str(ENGINEERING_DIR / "routing_rl.py"),
                "-o", out_path,
                "--qubits", str(req.qubits if req.qubits is not None else 3),
            ]
        else:
            cmd = [
                sys.executable,
                str(ENGINEERING_DIR / "routing_qubo_qaoa.py"),
                "-o", out_path,
            ]
            if use_hardware:
                cmd.append("--hardware")
            if req.fast:
                cmd.append("--fast")
            if req.topology:
                cmd.extend(["--topology", req.topology])
            if req.qubits is not None:
                cmd.extend(["--qubits", str(req.qubits)])
            if req.hub is not None and req.topology == "star":
                cmd.extend(["--hub", str(req.hub)])
        code, err = _run(cmd)
        if code != 0:
            raise HTTPException(status_code=503, detail=err or "Routing run failed")
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Script or output not found: {e}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid output JSON: {e}")
    finally:
        if os.path.isfile(out_path):
            try:
                os.unlink(out_path)
            except OSError:
                pass


@app.post("/api/run/pipeline")
def run_pipeline(req: RunPipelineRequest):
    """Run full pipeline: routing then inverse design. Optional: routing_method, model, heac."""
    cmd = [sys.executable, str(ENGINEERING_DIR / "run_pipeline.py")]
    if req.backend.lower() == "hardware":
        cmd.append("--hardware")
    if req.fast:
        cmd.append("--fast")
    if req.routing_method and req.routing_method.lower() in ("qaoa", "rl"):
        cmd.extend(["--routing-method", req.routing_method.lower()])
    if req.model and req.model.lower() in ("mlp", "gnn"):
        cmd.extend(["--model", req.model.lower()])
    if req.heac:
        cmd.append("--heac")
    if req.skip_routing:
        cmd.append("--skip-routing")
    if req.skip_inverse:
        cmd.append("--skip-inverse")
    code, err = _run(cmd)
    if code != 0:
        raise HTTPException(status_code=503, detail=err or "Pipeline run failed")
    result = {"message": "Pipeline completed", "routing_json": str(ROUTING_JSON), "inverse_json": str(INVERSE_JSON)}
    if ROUTING_JSON.exists():
        try:
            with open(ROUTING_JSON, encoding="utf-8") as f:
                result["routing"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    if INVERSE_JSON.exists():
        try:
            with open(INVERSE_JSON, encoding="utf-8") as f:
                result["inverse"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return result


@app.post("/api/run/inverse")
def run_inverse(req: RunInverseRequest):
    """Run inverse design (topology -> phase profile)."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    try:
        cmd = [
            sys.executable,
            str(ENGINEERING_DIR / "metasurface_inverse_net.py"),
            "-o", out_path,
        ]
        if req.phase_band:
            cmd.extend(["--phase-band", req.phase_band])
        if req.routing_result_path and os.path.isfile(req.routing_result_path):
            cmd.extend(["--routing-result", req.routing_result_path])
        elif ROUTING_JSON.exists():
            cmd.extend(["--routing-result", str(ROUTING_JSON)])
        code, err = _run(cmd)
        if code != 0:
            raise HTTPException(status_code=503, detail=err or "Inverse design run failed")
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Script or output not found: {e}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid output JSON: {e}")
    finally:
        if os.path.isfile(out_path):
            try:
                os.unlink(out_path)
            except OSError:
                pass


def _quantum_illumination():
    from protocols.quantum_illumination import entangled_probe_metrics, unentangled_probe_metrics
    return entangled_probe_metrics, unentangled_probe_metrics


@app.post("/api/run/quantum-illumination")
def run_quantum_illumination(req: QuantumIlluminationRequest):
    """Run DV quantum illumination comparison (entangled vs unentangled probe) for given eta."""
    try:
        ent_fn, unent_fn = _quantum_illumination()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Import failed: {e}")
    eta = max(0.0, min(1.0, req.eta))
    try:
        ent = ent_fn(eta)
        unent = unent_fn(eta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "eta": eta,
        "entangled": {"P_err": ent["P_err"], "chernoff_exponent": ent["chernoff_exponent"]},
        "unentangled": {"P_err": unent["P_err"], "chernoff_exponent": unent["chernoff_exponent"]},
        "advantage": {
            "P_err_lower_by": unent["P_err"] - ent["P_err"],
            "chernoff_higher_by": ent["chernoff_exponent"] - unent["chernoff_exponent"],
        },
    }


def _quantum_radar():
    from protocols.quantum_radar import run_quantum_radar, sweep_parameter, optimize_parameter
    return run_quantum_radar, sweep_parameter, optimize_parameter


@app.post("/api/run/quantum-radar")
def run_quantum_radar_api(req: QuantumRadarRequest):
    """Run CV quantum radar (TMSV + lossy thermal BS) single point."""
    try:
        run_fn, _, _ = _quantum_radar()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Import failed: {e}")
    try:
        out = run_fn(eta=req.eta, n_b=max(0.0, req.n_b), r=max(0.0, req.r))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return out


@app.post("/api/run/quantum-radar/sweep")
def run_quantum_radar_sweep(req: QuantumRadarSweepRequest):
    """Sweep one parameter (eta, n_b, r) for CV quantum radar."""
    if req.param not in ("eta", "n_b", "r"):
        raise HTTPException(status_code=400, detail="param must be eta, n_b, or r")
    try:
        _, sweep_fn, _ = _quantum_radar()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Import failed: {e}")
    defaults = {"eta": (0.01, 0.5), "n_b": (0.1, 50.0), "r": (0.1, 1.5)}
    lo, hi = defaults[req.param]
    min_val = req.min_val if req.min_val is not None else lo
    max_val = req.max_val if req.max_val is not None else hi
    try:
        results = sweep_fn(req.param, min_val, max_val, req.steps, req.eta, req.n_b, req.r)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"param": req.param, "results": results}


@app.post("/api/run/quantum-radar/optimize")
def run_quantum_radar_optimize(req: QuantumRadarOptimizeRequest):
    """Optimize one parameter (eta, n_b, r) to maximize mutual_info_H1 or snr_proxy_H1."""
    if req.param not in ("eta", "n_b", "r"):
        raise HTTPException(status_code=400, detail="param must be eta, n_b, or r")
    if req.maximize not in ("mutual_info", "snr"):
        raise HTTPException(status_code=400, detail="maximize must be mutual_info or snr")
    try:
        _, _, opt_fn = _quantum_radar()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Import failed: {e}")
    defaults = {"eta": (0.01, 0.99), "n_b": (0.0, 100.0), "r": (0.05, 2.0)}
    lo, hi = defaults[req.param]
    low = req.optimize_min if req.optimize_min is not None else lo
    high = req.optimize_max if req.optimize_max is not None else hi
    try:
        best_val, best_result = opt_fn(req.param, low, high, req.steps, req.eta, req.n_b, req.r, req.maximize)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"best_value": best_val, "best_result": best_result}


@app.get("/api/results/latest")
def get_results_latest():
    """Return paths and summary of last pipeline (routing + inverse) outputs."""
    result = {"routing_path": str(ROUTING_JSON), "inverse_path": str(INVERSE_JSON), "routing": None, "inverse": None}
    if ROUTING_JSON.exists():
        try:
            with open(ROUTING_JSON, encoding="utf-8") as f:
                result["routing"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    if INVERSE_JSON.exists():
        try:
            with open(INVERSE_JSON, encoding="utf-8") as f:
                result["inverse"] = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return result


@app.get("/api/results/inverse-phases")
def get_inverse_phases():
    """Return phase array from latest inverse design (for 3D/2D visualization)."""
    import numpy as np
    npy_path = ENGINEERING_DIR / (PIPELINE_BASE + "_inverse_phases.npy")
    if not npy_path.is_file() and INVERSE_JSON.exists():
        try:
            with open(INVERSE_JSON, encoding="utf-8") as f:
                inv = json.load(f)
            phase_array_path = inv.get("phase_array_path")
            if phase_array_path:
                npy_path = ENGINEERING_DIR / phase_array_path
        except (OSError, json.JSONDecodeError):
            pass
    if not npy_path.is_file():
        raise HTTPException(status_code=404, detail="No inverse phase array found. Run pipeline or inverse design first.")
    try:
        arr = np.load(npy_path)
        arr = np.asarray(arr).ravel()
        n = len(arr)
        # Optionally reshape to 2D for grid display (e.g. sqrt(n) x sqrt(n))
        nx = int(np.sqrt(n))
        ny = (n + nx - 1) // nx
        if nx * ny >= n:
            arr_2d = np.zeros((nx, ny), dtype=float)
            arr_2d.ravel()[:n] = arr
            arr_2d = arr_2d.tolist()
        else:
            arr_2d = arr.reshape(1, -1).tolist()
        return {"phases": arr.tolist(), "shape": list(np.shape(np.load(npy_path))), "grid_2d": arr_2d, "grid_shape": [nx, ny]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/docs/links")
def get_docs_links():
    """Return list of doc links for the front end."""
    links = [
        {"name": "Architecture overview", "path": "docs/architecture_overview.md", "url": None},
        {"name": "Quantum ASIC spec", "path": "docs/QUANTUM_ASIC.md", "url": None},
        {"name": "Whitepaper (Markdown)", "path": "docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md", "url": None},
        {"name": "Docs index", "path": "docs/README.md", "url": None},
        {"name": "Engineering README", "path": "engineering/README.md", "url": None},
        {"name": "Channel noise & DV illumination", "path": "docs/CHANNEL_NOISE.md", "url": None},
        {"name": "QKD (BB84, E91)", "path": "docs/QKD.md", "url": None},
        {"name": "Topology builder & viz", "path": "docs/TOPOLOGY_BUILDER.md", "url": None},
        {"name": "CV quantum radar (TMSV)", "path": "docs/CV_QUANTUM_RADAR.md", "url": None},
        {"name": "EaC distributed roadmap (MD)", "path": "docs/Engineering_as_Code_Distributed_Computational_Roadmap.md", "url": None},
        {"name": "Cryogenic metamaterials (MD)", "path": "docs/Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.md", "url": None},
        {"name": "Computational materials science (MD)", "path": "docs/Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.md", "url": None},
        {"name": "Quantum terrestrial backhaul (MD)", "path": "docs/quantum-terrestrial-backhaul.md", "url": None},
        {"name": "Unified quantum metasurfaces SATCOM (MD)", "path": "docs/Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.md", "url": None},
        {"name": "Applications (BQTC, QRNC)", "path": "docs/APPLICATIONS.md", "url": None},
        {"name": "Data and control plane extensions", "path": "docs/DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md", "url": None},
    ]
    for L in links:
        full = REPO_ROOT / L["path"]
        L["exists"] = full.exists()
        if full.exists():
            L["url"] = f"/docs/{L['path']}"  # Front end can use relative or absolute
    return {"links": links}


_ALLOWED_DOC_PATHS = frozenset({
    "docs/architecture_overview.md",
    "docs/QUANTUM_ASIC.md",
    "docs/WHITEPAPER_Holographic_Metasurfaces_Quantum_SATCOM.md",
    "docs/Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.md",
    "docs/README.md",
    "docs/CHANNEL_NOISE.md",
    "docs/QKD.md",
    "docs/TOPOLOGY_BUILDER.md",
    "docs/CV_QUANTUM_RADAR.md",
    "docs/quantum-terrestrial-backhaul.md",
    "docs/Engineering_as_Code_Distributed_Computational_Roadmap.md",
    "docs/Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.md",
    "docs/Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.md",
    "engineering/README.md",
    "docs/APPLICATIONS.md",
    "docs/DATA_AND_CONTROL_PLANE_QUANTUM_ASIC.md",
})


@app.get("/docs/{path:path}")
def serve_doc(path: str):
    """Serve a single doc file (markdown) from the repo. Only allowed paths under docs/ or engineering/README.md."""
    path = path.lstrip("/").replace("\\", "/")
    if path not in _ALLOWED_DOC_PATHS:
        raise HTTPException(status_code=404, detail="Doc not found")
    full = (REPO_ROOT / path).resolve()
    try:
        full.relative_to(REPO_ROOT.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Doc not found")
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Doc not found")
    return FileResponse(full, media_type="text/markdown")


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve built SPA in production (mount after routes so /api takes precedence)
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
