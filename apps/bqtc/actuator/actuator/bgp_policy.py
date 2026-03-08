"""
Map path distribution directives to concrete VyOS BGP config changes.
Outputs a list of (leaf_name, path, value) or equivalent for vyos_client.
"""

from typing import Any, Dict, List

# BGP local-preference in VyOS: protocols bgp <asn> parameters local-preference <value>
# Or via route-maps for finer control (per-neighbor or per-prefix). We use parameters for simplicity.


def directives_to_vyos_commands(
    directives: List[dict],
    leaf_asn: Dict[str, int],
) -> List[dict]:
    """
    Convert actuator directives to VyOS config operations.
    Each directive: {leaf, vni, path_id, local_preference}.
    Returns list of {"leaf": name, "path": ["protocols", "bgp", asn, "parameters", "local-preference", value]}.
    We set a single local-preference per leaf (simplified); for per-VNI/path you'd use route-maps.
    """
    # Group by leaf and take max local_preference (preferred path) to set as default
    by_leaf: Dict[str, int] = {}
    for d in directives:
        leaf = d.get("leaf", "")
        lp = d.get("local_preference", 100)
        by_leaf[leaf] = max(by_leaf.get(leaf, 0), lp)
    commands = []
    for leaf, lp in by_leaf.items():
        asn = leaf_asn.get(leaf, 65001)
        path = ["protocols", "bgp", str(asn), "parameters", "local-preference", str(lp)]
        commands.append({"leaf": leaf, "path": path, "value": str(lp)})
    return commands


def get_route_map_commands(
    directives: List[dict],
    leaf_asn: Dict[str, int],
    route_map_name: str = "EVPN-LOCAL-PREF",
) -> List[dict]:
    """
    Alternative: set local-preference via route-map (per-VNI or per-path).
    Returns list of set commands for route-map and then bind to BGP neighbor/peer.
    """
    # Simplified: one set of path + value per leaf for the route-map clause
    by_leaf: Dict[str, int] = {}
    for d in directives:
        leaf = d.get("leaf", "")
        lp = d.get("local_preference", 100)
        by_leaf[leaf] = max(by_leaf.get(leaf, 0), lp)
    commands = []
    for leaf, lp in by_leaf.items():
        asn = leaf_asn.get(leaf, 65001)
        # route-map EVPN-LOCAL-PREF permit 10; set local-preference 150
        path = [
            "policy", "route-map", route_map_name, "rule", "10",
            "set", "local-preference", str(lp),
        ]
        commands.append({"leaf": leaf, "path": path, "value": None})
    return commands
