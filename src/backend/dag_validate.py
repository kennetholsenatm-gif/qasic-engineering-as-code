"""
DAG validation for the orchestrator: acyclic, task types exist, backends supported, required inputs connected.
"""
from __future__ import annotations

from typing import Any

from .task_registry import get_task_type, get_required_inputs, get_supported_backends


def _build_adjacency(nodes: list[dict], edges: list[dict]) -> dict[str, list[str]]:
    """Build adjacency list: node_id -> list of successor node ids."""
    node_ids = {n.get("id") for n in nodes if n.get("id")}
    adj: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for e in edges:
        src, tgt = e.get("source"), e.get("target")
        if src in node_ids and tgt in node_ids and src != tgt:
            adj.setdefault(src, []).append(tgt)
    return adj


def _in_degree(nodes: list[dict], edges: list[dict]) -> dict[str, int]:
    """In-degree per node (number of incoming edges)."""
    node_ids = {n.get("id") for n in nodes if n.get("id")}
    deg = {nid: 0 for nid in node_ids}
    for e in edges:
        tgt = e.get("target")
        if tgt in node_ids:
            deg[tgt] = deg.get(tgt, 0) + 1
    return deg


def is_acyclic(nodes: list[dict], edges: list[dict]) -> tuple[bool, list[str]]:
    """Kahn-style topological sort. Returns (True, []) if acyclic, else (False, list of nodes in a cycle / unreachable)."""
    node_ids = [n.get("id") for n in nodes if n.get("id")]
    if not node_ids:
        return True, []
    adj = _build_adjacency(nodes, edges)
    in_deg = _in_degree(nodes, edges)
    queue = [nid for nid in node_ids if in_deg.get(nid, 0) == 0]
    order = []
    while queue:
        u = queue.pop(0)
        order.append(u)
        for v in adj.get(u, []):
            in_deg[v] = in_deg.get(v, 0) - 1
            if in_deg[v] == 0:
                queue.append(v)
    if len(order) == len(node_ids):
        return True, []
    # Nodes not in order are in a cycle or unreachable
    cycle_or_bad = [nid for nid in node_ids if nid not in order]
    return False, cycle_or_bad


def get_incoming_edges_by_target(nodes: list[dict], edges: list[dict]) -> dict[str, list[dict]]:
    """For each node id, list of edges whose target is that node (with sourceHandle/targetHandle)."""
    by_target: dict[str, list[dict]] = {}
    node_ids = {n.get("id") for n in nodes if n.get("id")}
    for e in edges:
        tgt = e.get("target")
        if tgt in node_ids:
            by_target.setdefault(tgt, []).append(e)
    return by_target


def validate_dag(nodes: list[dict], edges: list[dict]) -> list[dict[str, Any]]:
    """
    Validate a DAG definition. Returns list of errors; empty list means valid.
    Each error: { "node_id": str | None, "message": str, "code": str }
    """
    errors: list[dict[str, Any]] = []
    node_ids = {n.get("id") for n in nodes if n.get("id")}

    # 1. Acyclic
    acyclic, cycle_nodes = is_acyclic(nodes, edges)
    if not acyclic:
        errors.append({"node_id": None, "message": f"Graph has a cycle or disconnected nodes: {cycle_nodes}", "code": "cycle"})

    # 2. Every node has valid task_type and supported backend
    incoming = get_incoming_edges_by_target(nodes, edges)
    for n in nodes:
        nid = n.get("id")
        if not nid:
            errors.append({"node_id": None, "message": "Node missing id", "code": "missing_id"})
            continue
        task_type = n.get("data", {}).get("task_type") or n.get("task_type")
        if not task_type:
            errors.append({"node_id": nid, "message": "Node missing task_type", "code": "missing_task_type"})
            continue
        tt = get_task_type(task_type)
        if not tt:
            errors.append({"node_id": nid, "message": f"Unknown task_type: {task_type}", "code": "unknown_task_type"})
            continue
        config = n.get("data", {}).get("config") or n.get("config") or {}
        backend = config.get("backend", "local")
        supported = get_supported_backends(task_type)
        if backend not in supported:
            errors.append({"node_id": nid, "message": f"Backend '{backend}' not supported for {task_type}. Supported: {supported}", "code": "unsupported_backend"})

        # 3. Required inputs connected or defaultable
        required = get_required_inputs(task_type)
        in_edges = incoming.get(nid, [])
        # Map targetHandle -> source node output; for single-port we treat any edge as providing the one input if names match
        for inp in required:
            has_connection = any(
                e.get("targetHandle") == inp or e.get("targetHandle") is None
                for e in in_edges
            )
            if not has_connection and required:
                # Only report if we require this input and no edge provides it (simplified: one input per node = one edge)
                if len(required) == 1 and not in_edges:
                    errors.append({"node_id": nid, "message": f"Required input '{inp}' has no incoming edge", "code": "missing_input"})
                elif len(required) > 1:
                    if not any(e.get("targetHandle") == inp for e in in_edges):
                        errors.append({"node_id": nid, "message": f"Required input '{inp}' has no incoming edge", "code": "missing_input"})

    return errors
