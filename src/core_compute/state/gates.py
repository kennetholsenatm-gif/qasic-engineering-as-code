"""Single- and two-qubit gates as 2x2 or 4x4 matrices (complex)."""
import numpy as np

CDTYPE = np.complex128

# 2x2
I = np.array([[1, 0], [0, 1]], dtype=CDTYPE)
X = np.array([[0, 1], [1, 0]], dtype=CDTYPE)
Y = np.array([[0, -1j], [1j, 0]], dtype=CDTYPE)
Z = np.array([[1, 0], [0, -1]], dtype=CDTYPE)
H = np.array(
    [[1, 1], [1, -1]], dtype=CDTYPE
) / np.sqrt(2)

# 4x4
CNOT = np.array(
    [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
        [0, 0, 1, 0],
    ],
    dtype=CDTYPE,
)
CX = CNOT

CZ = np.array(
    [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, -1],
    ],
    dtype=CDTYPE,
)

swap = np.array(
    [
        [1, 0, 0, 0],
        [0, 0, 1, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
    ],
    dtype=CDTYPE,
)
