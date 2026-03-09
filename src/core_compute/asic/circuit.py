"""
ASIC circuit: list of ops (gate + qubits) that can be validated against topology and gate set.
Protocols are compiled to this op list so we only use the gates and topology the "chip" has.

Production rule: The Algorithm-to-ASIC pipeline and Run Pipeline use only openQASM-derived
circuits (via qasm_loader.load_qasm_string / load_qasm). The protocol_*_ops() functions below
are reference/demo implementations for teleportation, commitment, thief, bit-flip code; they
are not the source of truth for the ASIC. Prefer loading circuits from OpenQASM 2.0/3.0 where
possible (e.g. pulse compile_cli --qasm, run_protocol from QASM).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .topology import Topology, DEFAULT_TOPOLOGY
from .gate_set import GateSet, DEFAULT_GATE_SET


@dataclass
class Op:
    """Single operation: gate name, target qubit(s), optional parameter (e.g. Rx angle)."""
    gate: str
    targets: list[int]
    param: Any = None

    def __post_init__(self) -> None:
        self.targets = list(self.targets)


class ASICCircuit:
    """
    Circuit as a sequence of ops. Valid against a given Topology and GateSet.
    """

    def __init__(
        self,
        topology: Topology | None = None,
        gate_set: GateSet | None = None,
    ):
        self.topology = topology or DEFAULT_TOPOLOGY
        self.gate_set = gate_set or DEFAULT_GATE_SET
        self.ops: list[Op] = []

    def add(self, gate: str, targets: list[int], param: Any = None) -> "ASICCircuit":
        """Append an op; no validation here (use validate_circuit)."""
        self.ops.append(Op(gate=gate, targets=targets, param=param))
        return self

    def validate(self) -> list[str]:
        """Return list of error messages; empty if valid."""
        return validate_circuit(self.ops, self.topology, self.gate_set)


def validate_circuit(
    ops: list[Op],
    topology: Topology | None = None,
    gate_set: GateSet | None = None,
) -> list[str]:
    """
    Check every op: gate allowed, qubits in range, CNOT only on edges.
    Returns list of error strings (empty if valid).
    """
    top = topology or DEFAULT_TOPOLOGY
    gs = gate_set or DEFAULT_GATE_SET
    errors: list[str] = []

    for i, op in enumerate(ops):
        if not gs.allowed(op.gate):
            errors.append(f"Op {i}: unknown gate '{op.gate}'")
            continue

        n = top.n_qubits
        for q in op.targets:
            if q < 0 or q >= n:
                errors.append(f"Op {i}: qubit {q} out of range [0, {n})")
                break

        if gs.is_two_qubit(op.gate):
            if len(op.targets) != 2:
                errors.append(f"Op {i}: {op.gate} requires 2 qubits, got {op.targets}")
            elif not top.can_cnot(op.targets[0], op.targets[1]):
                errors.append(
                    f"Op {i}: CNOT on {op.targets} not allowed (no edge)"
                )
        elif gs.is_single_qubit(op.gate):
            if len(op.targets) != 1:
                errors.append(f"Op {i}: single-qubit gate {op.gate} expects 1 target, got {op.targets}")
            if gs.is_parametrized(op.gate) and op.param is None:
                errors.append(f"Op {i}: {op.gate} requires a parameter (e.g. angle)")

    return errors


def protocol_teleport_ops() -> list[Op]:
    """
    Teleportation circuit compiled to ASIC ops (reference/demo only; not used by pipeline).
    Qubits: 0=msg, 1=Alice Bell, 2=Bob Bell.
    Bell on (1,2): H(1), CNOT(1,2). Then CNOT(0,1), H(0). Corrections X, Z by Bob are classical.
    For pipeline and ASIC derivation, use openQASM via qasm_loader.
    """
    return [
        Op("H", [1]),
        Op("CNOT", [1, 2]),
        Op("CNOT", [0, 1]),
        Op("H", [0]),
    ]


def protocol_commitment_ops() -> list[Op]:
    """
    Bit commitment: create Bell on (0,1). So H(0), CNOT(0,1). Commit-to-1 is X(0) (before measure).
    Measurement is classical; we only list unitary ops the ASIC must support.
    """
    return [
        Op("H", [0]),
        Op("CNOT", [0, 1]),
        # X(0) applied conditionally for commit-to-1; not in base circuit
    ]


def protocol_thief_ops(qubit: int = 2, angle: float = 0.3) -> list[Op]:
    """Teleport + Thief: after teleport circuit, apply Rx(angle) on one qubit (e.g. Bob's)."""
    return protocol_teleport_ops() + [Op("Rx", [qubit], param=angle)]


def protocol_bitflip_code_ops(include_error_qubit: int | None = None) -> list[Op]:
    """
    3-qubit bit-flip repetition code on linear chain 0—1—2. Data on qubit 1, ancillas on 0 and 2.
    Encode: |0_L> -> |000>, |1_L> -> |111> via CNOT(1,0), CNOT(1,2).
    If include_error_qubit is 0, 1, or 2, append X on that qubit (single bit-flip error).
    Syndrome extraction and correction are done classically in the protocol layer after measurement.
    """
    # Encode: data on 1; CNOT 1->0, 1->2 (both edges allowed on linear chain)
    ops = [
        Op("CNOT", [1, 0]),
        Op("CNOT", [1, 2]),
    ]
    if include_error_qubit is not None:
        if include_error_qubit not in (0, 1, 2):
            raise ValueError("include_error_qubit must be 0, 1, or 2")
        ops.append(Op("X", [include_error_qubit]))
    return ops
