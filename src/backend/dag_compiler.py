"""
DAG compiler: translate React Flow nodes/edges into a Celery canvas (chain of groups).
Enables parallel execution of independent nodes (e.g. HEaC and thermal in parallel).
"""
from __future__ import annotations

from typing import Any

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.backend.dag_validate import is_acyclic


def _topological_waves(nodes: list[dict], edges: list[dict]) -> list[list[str]]:
    """Return nodes grouped by wave: wave[i] can run after all wave[0..i-1] complete."""
    acyclic, _ = is_acyclic(nodes, edges)
    if not acyclic:
        return []
    node_ids = [n.get("id") for n in nodes if n.get("id")]
    in_degree = {nid: 0 for nid in node_ids}
    adj: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for e in edges:
        src, tgt = e.get("source"), e.get("target")
        if src in in_degree and tgt in in_degree and src != tgt:
            in_degree[tgt] = in_degree.get(tgt, 0) + 1
            adj.setdefault(src, []).append(tgt)
    waves: list[list[str]] = []
    current = [nid for nid in node_ids if in_degree[nid] == 0]
    while current:
        waves.append(current)
        next_wave = []
        for u in current:
            for v in adj.get(u, []):
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    next_wave.append(v)
        current = next_wave
    return waves


def build_dag_canvas(run_id: int, nodes: list[dict], edges: list[dict], run_dag_node_task: Any) -> Any:
    """
    Build a Celery canvas that runs nodes wave by wave (parallel within a wave).
    run_dag_node_task: Celery task (prev_results, run_id, node_id) or (run_id, node_id) when first.
    Returns a chain of groups; apply_async() then get() to run and wait.
    """
    from celery import chain, group

    waves = _topological_waves(nodes, edges)
    if not waves:
        return None
    sigs = []
    for wave in waves:
        if len(wave) == 1:
            sigs.append(run_dag_node_task.s(run_id, wave[0]))
        else:
            sigs.append(group([run_dag_node_task.s(run_id, n) for n in wave]))
    return chain(*sigs)
