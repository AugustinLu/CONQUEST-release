#!/usr/bin/env python3
"""Validate the shear response of the monoclinic-HfO2 full-cell NPT test."""

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


def beta_angle(cell: np.ndarray) -> float:
    cosine = np.dot(cell[0], cell[2]) / (
        np.linalg.norm(cell[0]) * np.linalg.norm(cell[2])
    )
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


def normalized_metric(cell: np.ndarray) -> np.ndarray:
    return cell @ cell.T / abs(np.linalg.det(cell)) ** (2.0 / 3.0)


def final_positions(path: Path) -> np.ndarray:
    lines = path.read_text(encoding="utf-8").splitlines()
    cursor = 0
    final = None
    while cursor < len(lines):
        atoms = int(lines[cursor])
        final = np.asarray(
            [
                [float(value) for value in lines[cursor + 2 + atom].split()[1:4]]
                for atom in range(atoms)
            ]
        )
        cursor += atoms + 2
    if final is None:
        raise RuntimeError("No positions in extended XYZ")
    return final


def main() -> None:
    root = HERE / "results"
    restart_root = HERE / "results_restart"
    lattice, stress = read_extxyz(root / "trajectory.xyz")
    restart_lattice, _ = read_extxyz(restart_root / "trajectory.xyz")
    beta = np.asarray([beta_angle(cell) for cell in lattice])
    volumes = np.linalg.det(lattice)
    metric_change = float(
        np.max(np.abs(normalized_metric(lattice[-1]) - normalized_metric(lattice[0])))
    )
    symmetry_error = float(
        np.max(np.abs(stress - stress.transpose(0, 2, 1)))
    )
    restart_cell_residual = float(
        np.max(np.abs(restart_lattice[-1] - lattice[-1]))
    )
    restart_position_residual = float(
        np.max(
            np.abs(
                final_positions(restart_root / "trajectory.xyz")
                - final_positions(root / "trajectory.xyz")
            )
        )
    )

    failures: list[str] = []
    if len(lattice) != 3:
        failures.append(f"expected 3 initial+MD frames, found {len(lattice)}")
    if not np.all(np.isfinite(lattice)) or not np.all(np.isfinite(stress)):
        failures.append("trajectory contains non-finite cell or stress values")
    if np.any(volumes <= 0.0):
        failures.append("trajectory contains a non-positive cell volume")
    if symmetry_error > 1.0e-7:
        failures.append(f"stress tensor is not symmetric ({symmetry_error:.3e})")
    if abs(stress[0, 0, 2]) < 1.0e-4:
        failures.append("initial HfO2 cell has no useful xz shear stress")
    if abs(beta[-1] - beta[0]) < 1.0e-4:
        failures.append("full-cell barostat did not change monoclinic beta")
    if metric_change < 1.0e-5:
        failures.append("full-cell barostat produced only isotropic scaling")
    if abs(stress[-1, 0, 2]) >= abs(stress[0, 0, 2]):
        failures.append("xz shear stress did not move toward relaxation")
    if len(restart_lattice) != 3:
        failures.append(
            f"expected 3 restart frames, found {len(restart_lattice)}"
        )
    # The text checkpoint stores the cell with finite decimal precision, so
    # allow a few microangstroms while keeping the gate far below any physical
    # cell response in this test.
    if restart_cell_residual > 5.0e-6:
        failures.append(
            f"restart cell differs from uninterrupted run ({restart_cell_residual:.3e} A)"
        )
    if restart_position_residual > 2.0e-7:
        failures.append(
            "restart positions differ from uninterrupted run "
            f"({restart_position_residual:.3e} A)"
        )

    summary = {
        "status": "pass" if not failures else "fail",
        "frames": len(lattice),
        "volumes_angstrom3": volumes.tolist(),
        "beta_degrees": beta.tolist(),
        "xz_stress_eV_angstrom3": stress[:, 0, 2].tolist(),
        "normalized_metric_change": metric_change,
        "stress_symmetry_error": symmetry_error,
        "restart_cell_residual_angstrom": restart_cell_residual,
        "restart_position_residual_angstrom": restart_position_residual,
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
