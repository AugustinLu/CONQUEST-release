#!/usr/bin/env python3
"""Generate four neighboring yy strains around the former Fermi-level jump."""

from __future__ import annotations

import sys
from pathlib import Path


BASE_LATTICE = (
    (0.0, 5.18, 5.18),
    (5.18, 0.0, 5.18),
    (5.18, 5.18, 0.0),
)
PRESTRAIN = (
    (0.020, 0.015, -0.010),
    (0.015, -0.010, 0.012),
    (-0.010, 0.012, 0.005),
)
ATOMS = (
    "0.03125 0.03125 0.03125 1 T T T",
    "0.28125 0.28125 0.28125 1 T T T",
)


def multiply(left, right):
    return [
        [sum(left[i][k] * right[k][j] for k in range(3))
         for j in range(3)]
        for i in range(3)
    ]


def transpose(matrix):
    return [[matrix[j][i] for j in range(3)] for i in range(3)]


def identity_plus(matrix):
    return [
        [matrix[i][j] + (1.0 if i == j else 0.0) for j in range(3)]
        for i in range(3)
    ]


def main() -> None:
    root = Path(sys.argv[1])
    distorted = multiply(BASE_LATTICE, transpose(identity_plus(PRESTRAIN)))
    for microstrain in (184, 185, 186, 187):
        deformation = [[1.0, 0.0, 0.0],
                       [0.0, 1.0 + microstrain * 1.0e-6, 0.0],
                       [0.0, 0.0, 1.0]]
        lattice = multiply(distorted, transpose(deformation))
        case = root / f"d{microstrain}"
        case.mkdir(parents=True, exist_ok=True)
        lines = [" ".join(f"{value:.14f}" for value in row) for row in lattice]
        lines.extend(("2", *ATOMS))
        (case / "coords.dat").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
