#!/usr/bin/env python3
"""Validate automatic six-component relaxation for a general lattice."""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path


STRESS_TOLERANCE_GPA = 0.1
AUTO_WARNING = (
    "General-cell relaxation with AtomMove.OptCellMethod 1 or 2 and "
    "AtomMove.OptCell.Constraint none requires six-component symmetric "
    "strain; selecting AtomMove.CGLineMin backtrack"
)


def parse_stresses(text: str) -> list[list[list[float]]]:
    lines = text.splitlines()
    tensors: list[list[list[float]]] = []
    for index, line in enumerate(lines):
        if "force: Total stress:" not in line:
            continue
        first = line.split("force: Total stress:", 1)[1].replace("GPa", "").split()
        rows = [[float(value) for value in first[:3]]]
        rows.extend(
            [[float(value) for value in lines[index + offset].split()[:3]]
             for offset in (1, 2)]
        )
        tensors.append(rows)
    if not tensors:
        raise ValueError("no full stress tensor found")
    return tensors


def maximum_component(tensor: list[list[float]]) -> float:
    return max(abs(value) for row in tensor for value in row)


def read_lattice(path: Path) -> list[list[float]]:
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [[float(value) for value in lines[index].split()[:3]] for index in range(3)]


root = Path(sys.argv[1])
method1 = root / "method1"
method2 = root / "method2"
method1_text = (method1 / "Conquest_out").read_text(encoding="utf-8")
method2_text = (method2 / "Conquest_out").read_text(encoding="utf-8")
method1_warnings = (method1 / "Conquest_warnings").read_text(encoding="utf-8")
method2_warnings = (method2 / "Conquest_warnings").read_text(encoding="utf-8")

for name, text, warnings in (
    ("Method 1", method1_text, method1_warnings),
    ("Method 2", method2_text, method2_warnings),
):
    if AUTO_WARNING not in text and AUTO_WARNING not in warnings:
        raise ValueError(f"{name} did not report automatic backtracking")
    if "starting relaxation with safemin line minimisation" in text:
        raise ValueError(f"{name} used the diagonal-only safe minimizer")
    if "starting relaxation with backtracking line minimisation" not in text:
        raise ValueError(f"{name} did not enter the backtracking cell minimizer")

stresses = parse_stresses(method1_text)
initial_max = maximum_component(stresses[0])
final_max = maximum_component(stresses[-1])
geomopt = re.findall(r"GeomOpt - Iter:\s+(\d+) MaxStr:\s+([-+0-9.eE]+)", method1_text)
converged = re.search(r"GeomOpt converged in\s+(\d+) iterations", method1_text)
if not geomopt or converged is None:
    raise ValueError("Method 1 did not report normal geometry convergence")
reported_initial = float(geomopt[0][1])
if not math.isclose(reported_initial, initial_max, rel_tol=0.0, abs_tol=2.0e-8):
    raise ValueError(
        f"initial MaxStr {reported_initial:.8f} excludes a tensor component; "
        f"full maximum is {initial_max:.8f} GPa"
    )
if int(converged.group(1)) <= 1:
    raise ValueError("Method 1 still claimed convergence without a lattice step")
if final_max >= STRESS_TOLERANCE_GPA:
    raise ValueError(
        f"Method 1 converged with a {final_max:.8f} GPa stress component"
    )

initial_lattice = read_lattice(method1 / "coords.dat")
final_lattice = read_lattice(method1 / "UpdatedAtoms.dat")
change = max(
    abs(final_lattice[i][j] - initial_lattice[i][j])
    for i in range(3) for j in range(3)
)
if change <= 1.0e-8:
    raise ValueError("Method 1 reported convergence without changing the lattice")

print(
    "PASS: default general-cell relaxation used full symmetric strain; "
    f"max stress {initial_max:.8f} -> {final_max:.8f} GPa"
)
