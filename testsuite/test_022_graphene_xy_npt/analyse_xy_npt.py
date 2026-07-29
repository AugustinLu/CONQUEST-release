#!/usr/bin/env python3
"""Validate in-plane-only variable-cell dynamics for a 3x3 graphene sheet."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent


def read_extxyz(path: Path) -> tuple[np.ndarray, np.ndarray]:
    lines = path.read_text(encoding="utf-8").splitlines()
    lattices: list[np.ndarray] = []
    stresses: list[np.ndarray] = []
    cursor = 0
    while cursor < len(lines):
        atoms = int(lines[cursor])
        comment = lines[cursor + 1]
        lattice_match = re.search(r'Lattice="([^"]+)"', comment)
        stress_match = re.search(r'stress="([^"]+)"', comment)
        if lattice_match is None or stress_match is None:
            raise RuntimeError("Extended XYZ frame lacks lattice or stress")
        lattices.append(
            np.fromstring(lattice_match.group(1), sep=" ").reshape(3, 3)
        )
        stresses.append(
            np.fromstring(stress_match.group(1), sep=" ").reshape(3, 3)
        )
        cursor += atoms + 2
    return np.asarray(lattices), np.asarray(stresses)


def main() -> None:
    root = HERE / "results"
    lattice, stress = read_extxyz(root / "trajectory.xyz")
    areas = np.linalg.norm(np.cross(lattice[:, 0], lattice[:, 1]), axis=1)
    z_row_change = float(np.max(np.abs(lattice[:, 2] - lattice[0, 2])))
    out_of_plane_components = float(np.max(np.abs(lattice[:, :2, 2])))
    symmetry_error = float(
        np.max(np.abs(stress - stress.transpose(0, 2, 1)))
    )
    volumes = np.linalg.det(lattice)

    failures: list[str] = []
    if len(lattice) != 3:
        failures.append(f"expected 3 initial+MD frames, found {len(lattice)}")
    if not np.all(np.isfinite(lattice)) or not np.all(np.isfinite(stress)):
        failures.append("trajectory contains non-finite cell or stress values")
    if np.any(volumes <= 0.0):
        failures.append("trajectory contains a non-positive cell volume")
    if z_row_change > 1.0e-9:
        failures.append(f"vacuum lattice vector changed ({z_row_change:.3e} A)")
    if out_of_plane_components > 1.0e-9:
        failures.append(
            f"in-plane vectors acquired z components ({out_of_plane_components:.3e} A)"
        )
    if abs(areas[-1] - areas[0]) < 1.0e-4:
        failures.append("in-plane barostat did not change the graphene area")
    if symmetry_error > 1.0e-7:
        failures.append(f"stress tensor is not symmetric ({symmetry_error:.3e})")

    summary = {
        "status": "pass" if not failures else "fail",
        "frames": len(lattice),
        "areas_angstrom2": areas.tolist(),
        "vacuum_vector_angstrom": lattice[0, 2].tolist(),
        "vacuum_vector_max_change_angstrom": z_row_change,
        "in_plane_vector_z_max_angstrom": out_of_plane_components,
        "stress_symmetry_error": symmetry_error,
        "failures": failures,
    }
    (root / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    if failures:
        raise SystemExit("FAIL: " + "; ".join(failures))


if __name__ == "__main__":
    main()
