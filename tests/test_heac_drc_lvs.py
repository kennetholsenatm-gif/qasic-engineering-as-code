"""Tests for HEaC GDS, DRC, and LVS (mock and PDK config)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Repo root
REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINEERING = REPO_ROOT / "engineering"
HEAC = ENGINEERING / "heac"


def _minimal_manifest_path(tmp_path: Path) -> Path:
    """Write a minimal geometry manifest to tmp_path and return its path."""
    manifest = {
        "pitch_um": 1.0,
        "units": "um",
        "library_source": "test",
        "shape": [2, 2],
        "num_cells": 4,
        "cells": [
            {"i": 0, "j": 0, "phase_rad": 3.14, "dimension": 0.5},
            {"i": 0, "j": 1, "phase_rad": 3.14, "dimension": 0.5},
            {"i": 1, "j": 0, "phase_rad": 3.14, "dimension": 0.5},
            {"i": 1, "j": 1, "phase_rad": 3.14, "dimension": 0.5},
        ],
    }
    p = tmp_path / "minimal_manifest.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return p


def test_load_pdk_config():
    """PDK config loading (manifest_to_gds helper)."""
    from engineering.heac.manifest_to_gds import load_pdk_config, get_layer, clamp_dimension
    pdk_path = HEAC / "pdk_config.yaml"
    if not pdk_path.exists():
        pytest.skip("pdk_config.yaml not found")
    pdk = load_pdk_config(str(pdk_path))
    assert pdk is not None
    assert get_layer(pdk) == (1, 0)
    assert clamp_dimension(0.01, pdk) >= 0.1
    assert clamp_dimension(1.0, pdk) == 1.0


def test_drc_mock(tmp_path):
    """DRC mock: run without KLayout; should pass with non-empty GDS or report only."""
    from engineering.heac.run_drc_klayout import run_drc_klayout
    # No GDS: should fail
    passed, msg = run_drc_klayout(str(tmp_path / "missing.gds"), None, None)
    assert passed is False
    # Empty file: mock should fail
    empty = tmp_path / "empty.gds"
    empty.write_bytes(b"")
    passed, msg = run_drc_klayout(str(empty), None, None)
    assert passed is False
    # Non-empty file: mock passes
    (tmp_path / "dummy.gds").write_bytes(b"\x00\x01fake_gds_content")
    report_path = str(tmp_path / "drc_report.json")
    passed, msg = run_drc_klayout(str(tmp_path / "dummy.gds"), None, report_path)
    assert passed is True
    if os.path.isfile(report_path):
        with open(report_path) as f:
            report = json.load(f)
        assert report.get("mock") is True
        assert report.get("passed") is True


def test_lvs_mock(tmp_path):
    """LVS mock: schematic from manifest vs missing/empty GDS."""
    from engineering.heac.run_lvs_klayout import run_lvs, schematic_netlist_from_manifest
    manifest_path = _minimal_manifest_path(tmp_path)
    schem = schematic_netlist_from_manifest(str(manifest_path), None)
    assert schem["num_cells"] == 4
    # GDS missing: fail
    passed, _ = run_lvs(str(manifest_path), str(tmp_path / "missing.gds"), None, None)
    assert passed is False
    # Empty GDS: mock fail
    (tmp_path / "empty.gds").write_bytes(b"")
    passed, _ = run_lvs(str(manifest_path), str(tmp_path / "empty.gds"), None, None)
    assert passed is False
    # Non-empty GDS: mock pass
    (tmp_path / "dummy.gds").write_bytes(b"\x00\x01gds")
    report_path = str(tmp_path / "lvs_report.json")
    passed, _ = run_lvs(str(manifest_path), str(tmp_path / "dummy.gds"), None, report_path)
    assert passed is True
    if os.path.isfile(report_path):
        with open(report_path) as f:
            report = json.load(f)
        assert report.get("mock") is True


@pytest.mark.skipif(not (HEAC / "pdk_config.yaml").exists(), reason="pdk_config.yaml not found")
def test_manifest_to_gds_with_pdk(tmp_path):
    """If gdsfactory and pdk_config exist, manifest_to_gds produces GDS."""
    try:
        import gdsfactory
    except ImportError:
        pytest.skip("gdsfactory not installed")
    manifest_path = _minimal_manifest_path(tmp_path)
    gds_path = tmp_path / "out.gds"
    pdk_config = str(HEAC / "pdk_config.yaml")
    cmd = [
        sys.executable,
        str(HEAC / "manifest_to_gds.py"),
        str(manifest_path), "-o", str(gds_path),
        "--pdk-config", pdk_config,
    ]
    rc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30)
    assert rc.returncode == 0, (rc.stdout or "") + (rc.stderr or "")
    assert gds_path.exists()
    assert gds_path.stat().st_size > 0


def test_dft_structures_build(tmp_path):
    """DFT structures: build_dft_manifest produces pads, alignment, witnesses."""
    from engineering.heac.dft_structures import build_dft_manifest
    manifest_path = _minimal_manifest_path(tmp_path)
    dft = build_dft_manifest(str(manifest_path), str(HEAC / "pdk_config.yaml") if (HEAC / "pdk_config.yaml").exists() else None)
    assert dft["source"] == "dft_structures"
    assert dft["core_width_um"] == 2.0
    assert dft["core_height_um"] == 2.0
    assert len(dft["pads"]) > 0
    assert len(dft["alignment_marks"]) > 0
    assert len(dft["witness_structures"]) >= 2
    out_json = tmp_path / "dft_manifest.json"
    import json
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(dft, f, indent=2)
    assert out_json.exists()


@pytest.mark.skipif(not (HEAC / "pdk_config.yaml").exists(), reason="pdk_config.yaml not found")
def test_dft_structures_cli_and_merge(tmp_path):
    """DFT structures CLI: output JSON; with gdsfactory, merge into GDS."""
    try:
        import gdsfactory
    except ImportError:
        pytest.skip("gdsfactory not installed")
    manifest_path = _minimal_manifest_path(tmp_path)
    gds_path = tmp_path / "out.gds"
    pdk_config = str(HEAC / "pdk_config.yaml")
    # Create GDS first
    cmd_gds = [
        sys.executable,
        str(HEAC / "manifest_to_gds.py"),
        str(manifest_path), "-o", str(gds_path),
        "--pdk-config", pdk_config,
    ]
    rc = subprocess.run(cmd_gds, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30)
    assert rc.returncode == 0
    # DFT manifest only
    dft_json = tmp_path / "dft_manifest.json"
    cmd_dft = [
        sys.executable,
        str(HEAC / "dft_structures.py"),
        str(manifest_path), "-o", str(dft_json),
        "--pdk-config", pdk_config,
    ]
    rc = subprocess.run(cmd_dft, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30)
    assert rc.returncode == 0
    assert dft_json.exists()
    # Merge DFT into GDS
    cmd_merge = [
        sys.executable,
        str(HEAC / "dft_structures.py"),
        str(manifest_path),
        "--pdk-config", pdk_config,
        "--merge", str(gds_path),
        "--output-gds", str(gds_path),
    ]
    rc = subprocess.run(cmd_merge, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30)
    assert rc.returncode == 0
    assert gds_path.stat().st_size > 0


def test_superconducting_extraction(tmp_path):
    """Superconducting extraction: kinetic L and optional JJ L from manifest."""
    from engineering.superconducting_extraction import extract_kinetic_inductance
    manifest_path = _minimal_manifest_path(tmp_path)
    data = extract_kinetic_inductance(str(manifest_path), routing_path=None)
    assert data["source"] == "superconducting_extraction"
    assert len(data["nodes"]) == 4
    assert all("gamma1" in n and "gamma2" in n and "L_kinetic_nH" in n for n in data["nodes"])
    assert "edges" in data
    assert isinstance(data["jj"], list)


def test_process_variation_sweep(tmp_path):
    """Process variation sweep: perturb manifest, run extraction, get stats."""
    from engineering.process_variation_sweep import run_sweep, perturb_manifest
    import numpy as np
    manifest_path = _minimal_manifest_path(tmp_path)
    # Quick sweep with 2 samples
    result = run_sweep(
        str(manifest_path),
        routing_path=None,
        n_samples=2,
        dimension_std_um=0.01,
        seed=123,
        run_superconducting=True,
        script_dir=str(ENGINEERING),
        repo_root=str(REPO_ROOT),
    )
    assert result["source"] == "process_variation_sweep"
    assert result["n_samples"] == 2
    assert "parasitic_metric" in result
    assert result["parasitic_metric"]["count"] == 2
    assert result.get("superconducting_metric") is None or result["superconducting_metric"]["count"] in (0, 2)
