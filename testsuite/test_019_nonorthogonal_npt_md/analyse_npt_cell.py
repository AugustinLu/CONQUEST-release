#!/usr/bin/env python3
"""Validate that one NPT step preserves a complete nonorthogonal lattice."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np


def input_lattice(path: Path) -> np.ndarray:
    return np.array(
        [[float(value) for value in line.split()]
         for line in path.read_text().splitlines()[:3]]
    )


def frame_lattice(path: Path) -> np.ndarray:
    lines = path.read_text().splitlines()
    start = lines.index("cell_vectors") + 1
    return np.array(
        [[float(value) for value in lines[start + i].split()] for i in range(3)]
    )


def extxyz_lattice(path: Path) -> np.ndarray:
    comments = path.read_text().splitlines()[1::4]
    if not comments:
        raise RuntimeError("No extended-XYZ frames found")
    values = re.search(r'Lattice="([^"]+)"', comments[-1])
    if values is None:
        raise RuntimeError("No Lattice field in extended XYZ")
    return np.array([float(value) for value in values.group(1).split()]).reshape(3, 3)


def shape_metric(rows: np.ndarray) -> np.ndarray:
    gram = rows @ rows.T
    return gram / abs(np.linalg.det(rows)) ** (2.0 / 3.0)


def analyse_case(root: Path, initial: np.ndarray, isotropic: bool) -> dict:
    frame = frame_lattice(root / "md.frames")
    final = extxyz_lattice(root / "trajectory.xyz")
    text = (root / "Conquest_out").read_text()
    result = {
        "md_frame_lattice_rows_bohr": frame.tolist(),
        "final_extxyz_lattice_rows_angstrom": final.tolist(),
        "final_volume_angstrom3": abs(float(np.linalg.det(final))),
        "md_frame_initial_error_bohr": float(np.max(np.abs(frame - initial))),
        "final_offdiagonal_norm_angstrom": float(
            np.linalg.norm(final - np.diag(np.diag(final)))
        ),
        "completed_md_steps": len(re.findall(r"MD step:\s+1\b", text)),
    }
    if isotropic:
        result["isotropic_shape_residual"] = float(
            np.max(np.abs(shape_metric(final) - shape_metric(initial)))
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    initial = input_lattice(args.source / "coords.dat")
    result = {
        "initial_lattice_rows_bohr": initial.tolist(),
        "initial_volume_bohr3": abs(float(np.linalg.det(initial))),
        "cases": {
            "volume": analyse_case(args.root / "volume", initial, True),
            "xyz": analyse_case(args.root / "xyz", initial, False),
        },
    }
    method3_final = input_lattice(args.root / "method3_smoke" / "coord_next.dat")
    result["method3"] = {
        "final_lattice_rows_bohr": method3_final.tolist(),
        "final_volume_bohr3": abs(float(np.linalg.det(method3_final))),
        "volume_constraint_shape_residual": float(
            np.max(np.abs(shape_metric(method3_final) - shape_metric(initial)))
        ),
        "final_offdiagonal_norm_bohr": float(
            np.linalg.norm(method3_final - np.diag(np.diag(method3_final)))
        ),
    }

    failures = []
    for name, case in result["cases"].items():
        if case["md_frame_initial_error_bohr"] > 1.0e-6:
            failures.append(f"{name}: md.frames lost the complete input lattice")
        if case["final_offdiagonal_norm_angstrom"] < 1.0:
            failures.append(f"{name}: final cell was diagonalized")
        if case["completed_md_steps"] != 1:
            failures.append(f"{name}: one-step NPT trajectory did not complete")
        final = np.asarray(case["final_extxyz_lattice_rows_angstrom"])
        if not np.isfinite(final).all() or np.linalg.det(final) <= 0.0:
            failures.append(f"{name}: final lattice is invalid")
    if result["cases"]["volume"]["isotropic_shape_residual"] > 2.0e-6:
        failures.append("isotropic barostat changed the normalized cell shape")
    if not np.isfinite(method3_final).all() or np.linalg.det(method3_final) <= 0.0:
        failures.append("method 3: final lattice is invalid")
    if result["method3"]["final_offdiagonal_norm_bohr"] < 1.0:
        failures.append("method 3: final cell was diagonalized")
    if result["method3"]["volume_constraint_shape_residual"] > 2.0e-8:
        failures.append("method 3: volume constraint changed normalized cell shape")

    result["status"] = "pass" if not failures else "fail"
    result["failures"] = failures
    args.summary.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if failures:
        raise SystemExit("FAIL: " + "; ".join(failures))


if __name__ == "__main__":
    main()
