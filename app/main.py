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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ENGINEERING_DIR = REPO_ROOT / "engineering"
DOCS_DIR = REPO_ROOT / "docs"
PIPELINE_BASE = "pipeline_result"
ROUTING_JSON = ENGINEERING_DIR / f"{PIPELINE_BASE}_routing.json"
INVERSE_JSON = ENGINEERING_DIR / f"{PIPELINE_BASE}_inverse.json"

app = FastAPI(title="QASIC Engineering-as-Code API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


class RunPipelineRequest(BaseModel):
    backend: str = "sim"
    fast: bool = False


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


@app.post("/api/run/protocol")
def run_protocol(req: RunProtocolRequest):
    """Run ASIC protocol (teleport, bell, commitment, thief) on sim or IBM hardware."""
    use_hardware = req.backend.lower() == "hardware"
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    try:
        cmd = [
            sys.executable,
            str(ENGINEERING_DIR / "run_protocol_on_ibm.py"),
            "--protocol", req.protocol,
            "-o", out_path,
        ]
        if use_hardware:
            cmd.append("--hardware")
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


@app.post("/api/run/routing")
def run_routing(req: RunRoutingRequest):
    """Run QUBO routing (QAOA or classical) on sim or IBM hardware."""
    use_hardware = req.backend.lower() == "hardware"
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    try:
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
    """Run full pipeline: routing then inverse design."""
    cmd = [sys.executable, str(ENGINEERING_DIR / "run_pipeline.py")]
    if req.backend.lower() == "hardware":
        cmd.append("--hardware")
    if req.fast:
        cmd.append("--fast")
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
        {"name": "Topology builder & viz", "path": "docs/TOPOLOGY_BUILDER.md", "url": None},
        {"name": "CV quantum radar (TMSV)", "path": "docs/CV_QUANTUM_RADAR.md", "url": None},
        {"name": "EaC distributed roadmap (MD)", "path": "docs/Engineering_as_Code_Distributed_Computational_Roadmap.md", "url": None},
        {"name": "Cryogenic metamaterials (MD)", "path": "docs/Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.md", "url": None},
        {"name": "Computational materials science (MD)", "path": "docs/Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.md", "url": None},
        {"name": "Quantum terrestrial backhaul (MD)", "path": "docs/quantum-terrestrial-backhaul.md", "url": None},
        {"name": "Unified quantum metasurfaces SATCOM (MD)", "path": "docs/Whitepaper_Unified_Quantum_Metasurfaces_SATCOM.md", "url": None},
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
    "docs/TOPOLOGY_BUILDER.md",
    "docs/CV_QUANTUM_RADAR.md",
    "docs/quantum-terrestrial-backhaul.md",
    "docs/Engineering_as_Code_Distributed_Computational_Roadmap.md",
    "docs/Computational_Materials_Science_Cryogenic_Quantum_Metamaterials.md",
    "docs/Cryogenic_Metamaterial_Architectures_Quantum_SATCOM.md",
    "engineering/README.md",
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
