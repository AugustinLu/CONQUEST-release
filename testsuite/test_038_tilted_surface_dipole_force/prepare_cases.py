#!/usr/bin/env python3
"""Write the tilted water-layer geometry and its four z displacements.

The water layer of test 008 is placed in a cell whose third lattice vector is
tilted, a3 -> a3 + a1.  The surface (spanned by a1 and a2) and the slab height
along the normal (15 a0) are unchanged, but |a3| = 16.04 a0.  The atoms keep
the Cartesian positions of test 008.
"""

from __future__ import annotations

import sys
from pathlib import Path

A = 5.66918063400000
C = 14.99999999952342
# Lattice vectors, one per row as in a CONQUEST coordinate file.
LATTICE = ((A, 0.0, 0.0), (0.0, A, 0.0), (A, 0.0, C))
# Fractional coordinates of test 008 in its orthorhombic cell, and species.
ORTHO_FRACTIONAL = (
    ((0.3229424998, 0.3229424998, 0.5000000000), 1),
    ((0.0674088150, 0.3229424998, 0.5761442602), 2),
    ((0.5784761847, 0.3229424998, 0.5761442602), 2),
)
STEP = 0.01  # Cartesian z displacement in bohr
# Case name -> (atom index, signed z displacement)
CASES = {
    "c0": (None, 0.0),
    "a1p": (0, +STEP), "a1m": (0, -STEP),
    "a2p": (1, +STEP), "a2m": (1, -STEP),
}


def cartesian_positions():
    return [[s[0] * A, s[1] * A, s[2] * C] for s, _ in ORTHO_FRACTIONAL]


def to_fractional(r):
    # Inverse of the row lattice above: r = s1 a1 + s2 a2 + s3 a3.
    s3 = r[2] / C
    s1 = (r[0] - s3 * A) / A
    s2 = r[1] / A
    return s1, s2, s3


def write_case(directory: Path, positions):
    directory.mkdir(parents=True, exist_ok=True)
    lines = ["  %.14f %.14f %.14f" % row for row in LATTICE]
    lines.append(str(len(positions)))
    for r, (_, species) in zip(positions, ORTHO_FRACTIONAL):
        lines.append("  %.14f %.14f %.14f %d T T T" % (*to_fractional(r), species))
    (directory / "coords.in").write_text("\n".join(lines) + "\n")


def main():
    root = Path(sys.argv[1])
    for name, (atom, dz) in CASES.items():
        positions = cartesian_positions()
        if atom is not None:
            positions[atom][2] += dz
        write_case(root / name, positions)


if __name__ == "__main__":
    main()
