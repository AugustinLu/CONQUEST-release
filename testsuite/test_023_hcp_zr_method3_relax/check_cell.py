#!/usr/bin/env python3
"""Check the geometric invariants of the HCP method-3 example."""

from __future__ import annotations

import math
import sys
from pathlib import Path


def read_lattice(path: Path) -> list[list[float]]:
    with path.open(encoding="utf-8") as handle:
        return [[float(value) for value in handle.readline().split()] for _ in range(3)]


def length(vector: list[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def angle(left: list[float], right: list[float]) -> float:
    cosine = sum(a * b for a, b in zip(left, right)) / (length(left) * length(right))
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def determinant(rows: list[list[float]]) -> float:
    a, b, c = rows
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


initial = read_lattice(Path(sys.argv[1]))
final = read_lattice(Path(sys.argv[2]))
initial_angles = (angle(initial[1], initial[2]), angle(initial[0], initial[2]), angle(initial[0], initial[1]))
final_angles = (angle(final[1], final[2]), angle(final[0], final[2]), angle(final[0], final[1]))
angle_error = max(abs(a - b) for a, b in zip(initial_angles, final_angles))
ratio_error = abs(length(final[0]) / length(final[1]) - length(initial[0]) / length(initial[1]))

if determinant(final) <= 0.0:
    raise SystemExit("FAIL: final lattice has non-positive volume")
if angle_error > 1.0e-6:
    raise SystemExit(f"FAIL: method 3 changed an HCP lattice angle by {angle_error:.3e} degrees")
if ratio_error > 1.0e-8:
    raise SystemExit(f"FAIL: a/b constraint residual is {ratio_error:.3e}")

print(
    "PASS: angles preserved; "
    f"a={length(final[0]):.8f}, b={length(final[1]):.8f}, "
    f"c={length(final[2]):.8f}, gamma={final_angles[2]:.8f} degrees"
)
