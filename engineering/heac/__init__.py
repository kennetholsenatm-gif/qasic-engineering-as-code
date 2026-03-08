"""
Hardware-Engineering-as-Code (HEaC) open-source stack: Meep-based meta-atom library,
phase-to-dimension interpolation, and phases.npy -> geometry manifest compilation.
Ref: docs/Automated_HEaC_Deep_Cryogenic_Quantum_ASICs.tex
"""
from __future__ import annotations

try:
    from engineering.heac.phase_to_dimension import (
        build_interpolator,
        load_library,
        phase_to_dimension,
    )
except ImportError:
    from heac.phase_to_dimension import (
        build_interpolator,
        load_library,
        phase_to_dimension,
    )

__all__ = [
    "build_interpolator",
    "load_library",
    "phase_to_dimension",
]
