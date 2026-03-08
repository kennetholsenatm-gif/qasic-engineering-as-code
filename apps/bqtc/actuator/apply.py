"""
Orchestration: connect to each leaf, apply BGP local-preference changes, commit (or dry-run).
"""

import time
from typing import Any, Dict, List, Optional

from .bgp_policy import directives_to_vyos_commands
from .vyos_client import VyOSClient


def load_leaf_config(leafs: List[dict]) -> Dict[str, dict]:
    """Build leaf name -> config (host, api_key, etc.) from topology."""
    cfg = {}
    for leaf in leafs:
        name = leaf.get("name", leaf.get("host", ""))
        cfg[name] = {
            "host": leaf.get("host", ""),
            "api_key": leaf.get("api_key"),
            "asn": leaf.get("asn", 65001),
        }
    return cfg


def apply_directives(
    directives: List[dict],
    leafs: List[dict],
    dry_run: bool = True,
    rate_limit_seconds: float = 5.0,
) -> List[dict]:
    """
    Apply BGP policy directives to VyOS leafs.
    directives: from quantum.mapping.path_distribution_to_bgp_preferences
    leafs: from topology (name, host, asn, optional api_key).
    Returns list of {"leaf": name, "status": "ok"|"skip"|"error", "message": str}.
    """
    leaf_asn = {l.get("name", l.get("host")): l.get("asn", 65001) for l in leafs}
    commands = directives_to_vyos_commands(directives, leaf_asn)
    results = []
    for cmd in commands:
        leaf_name = cmd["leaf"]
        leaf_cfg = next((l for l in leafs if l.get("name") == leaf_name or l.get("host") == leaf_name), None)
        if not leaf_cfg or not leaf_cfg.get("host"):
            results.append({"leaf": leaf_name, "status": "skip", "message": "no host"})
            continue
        if dry_run:
            results.append({
                "leaf": leaf_name,
                "status": "ok",
                "message": f"dry-run: would set path {cmd['path']}",
            })
            continue
        try:
            client = VyOSClient(
                host=leaf_cfg["host"],
                api_key=leaf_cfg.get("api_key"),
                use_https=bool(leaf_cfg.get("api_key")),
            )
            client.connect()
            path = cmd["path"]
            value = cmd.get("value")
            client.configure_set(path, value)
            client.commit()
            client.save()
            client.disconnect()
            results.append({"leaf": leaf_name, "status": "ok", "message": "committed"})
        except Exception as e:
            results.append({"leaf": leaf_name, "status": "error", "message": str(e)})
        time.sleep(rate_limit_seconds)
    return results
