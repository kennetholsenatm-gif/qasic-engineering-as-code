"""
Map path distribution (vni -> path_id) to per-leaf BGP local-preference deltas.
The actuator will apply these to VyOS.
"""

from typing import Dict, List, Optional

# Topology: list of leafs with name, host, asn; paths with id and optional preference rank
# Path distribution: vni -> path_id (preferred path for that VNI)
# BGP local preference: higher = preferred. We output (leaf_name, neighbor_or_route_map, local_pref_delta)
# or (leaf_name, path_id, local_preference_value) so actuator can set route-maps per path.


def path_distribution_to_bgp_preferences(
    vni_to_path: Dict[int, str],
    path_ids: List[str],
    leafs: List[dict],
    path_preference_order: Optional[Dict[str, int]] = None,
) -> List[dict]:
    """
    Convert path distribution to BGP local-preference directives per leaf.
    path_preference_order: path_id -> local_preference value (higher = prefer).
    If None, path_ids get 200, 150, 100, ... so first path is preferred by default.
    Returns list of {"leaf": name, "vni": vni, "path_id": path_id, "local_preference": value}.
    """
    if path_preference_order is None:
        path_preference_order = {
            pid: 200 - 50 * i for i, pid in enumerate(path_ids)
        }
    directives = []
    for vni, path_id in vni_to_path.items():
        lp = path_preference_order.get(path_id, 100)
        for leaf in leafs:
            name = leaf.get("name", leaf.get("host", ""))
            directives.append({
                "leaf": name,
                "vni": vni,
                "path_id": path_id,
                "local_preference": lp,
            })
    return directives
