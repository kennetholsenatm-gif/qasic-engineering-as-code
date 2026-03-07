"""
Quantum ASIC: minimal gate set and fixed topology sufficient for the toy protocols
(teleportation, tamper-evidence, bit commitment). Circuits are expressed as
ops on this device and validated against its constraints.
"""
from .topology import Topology, DEFAULT_TOPOLOGY
from .topology_builder import (
    linear_chain,
    star,
    repeater_chain,
    get_topology,
    edges_to_interaction_matrix,
    NAMED_TOPOLOGIES,
)
from .gate_set import GateSet, DEFAULT_GATE_SET
from .circuit import (
    ASICCircuit,
    Op,
    validate_circuit,
    protocol_teleport_ops,
    protocol_commitment_ops,
    protocol_thief_ops,
)

__all__ = [
    "Topology",
    "DEFAULT_TOPOLOGY",
    "linear_chain",
    "star",
    "repeater_chain",
    "get_topology",
    "edges_to_interaction_matrix",
    "NAMED_TOPOLOGIES",
    "GateSet",
    "DEFAULT_GATE_SET",
    "ASICCircuit",
    "Op",
    "validate_circuit",
    "protocol_teleport_ops",
    "protocol_commitment_ops",
    "protocol_thief_ops",
]
