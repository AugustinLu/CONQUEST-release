#!/usr/bin/env python3
"""Validate polarization and extended-XYZ geometry in equivalent cells."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np


BOHR_TO_ANGSTROM = 0.529177210903
EV_PER_ANGSTROM3_TO_GPA = 160.2176634


def read_lattice(filename: Path):
    return np.loadtxt(filename, max_rows=3)


def parse_output(filename: Path):
    text = filename.read_text(encoding="utf-8")
    lines = text.splitlines()
    energy = re.findall(r"Harris-Foulkes energy\s+=\s+([-+0-9.eE]+)", text)
    total = re.findall(
        r"Total polarisation:\s+([-+0-9.eE]+)\s+e / Bohr\^2", text
    )
    quantum = re.findall(
        r"Quantum of polarisation:\s+([-+0-9.eE]+)\s+e / Bohr\^2", text
    )
    if not energy or len(total) != 3 or len(quantum) != 3:
        raise ValueError(f"Missing energy or three polarization directions in {filename}")
    stress_starts = [
        index for index, line in enumerate(lines) if "force: Total stress:" in line
    ]
    if not stress_starts:
        raise ValueError(f"Missing full stress tensor in {filename}")
    start = stress_starts[-1]
    first = (
        lines[start].split("force: Total stress:", 1)[1].replace("GPa", "").split()
    )
    stress = [[float(value) for value in first[:3]]]
    stress.extend(
        [[float(value) for value in lines[start + offset].split()[:3]]
         for offset in (1, 2)]
    )
    return {
        "energy_ha": float(energy[-1]),
        "polarisation_e_per_bohr2": np.asarray([float(value) for value in total]),
        "quantum_e_per_bohr2": np.asarray([float(value) for value in quantum]),
        "stress_gpa": np.asarray(stress),
    }


def parse_extxyz(filename: Path):
    lines = filename.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        raise ValueError(f"Invalid extended XYZ file: {filename}")
    lattice_match = re.search(r'Lattice="([^"]+)"', lines[1])
    stress_match = re.search(r'stress="\s*([^"]+)"', lines[1])
    if not lattice_match or not stress_match:
        raise ValueError(f"Missing lattice or stress metadata in {filename}")
    lattice = np.asarray([float(value) for value in lattice_match.group(1).split()])
    stress = np.asarray([float(value) for value in stress_match.group(1).split()])
    return lattice.reshape(3, 3), stress.reshape(3, 3)


def wrapped_residual(values):
    return values - np.rint(values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    cases = {}
    for name in ("base", "sheared"):
        directory = args.root / name
        lattice = read_lattice(directory / "coords.dat")
        output = parse_output(directory / "Conquest_out")
        xyz_lattice, xyz_stress = parse_extxyz(directory / "trajectory.xyz")
        volume = abs(float(np.linalg.det(lattice)))
        expected_quantum = np.linalg.norm(lattice, axis=1) / volume
        cases[name] = {
            "lattice_bohr": lattice,
            "volume_bohr3": volume,
            "energy_ha": output["energy_ha"],
            "polarisation": output["polarisation_e_per_bohr2"],
            "quantum": output["quantum_e_per_bohr2"],
            "coefficients": (
                output["polarisation_e_per_bohr2"]
                / output["quantum_e_per_bohr2"]
            ),
            "quantum_error": float(
                np.max(np.abs(output["quantum_e_per_bohr2"] - expected_quantum))
            ),
            "extxyz_lattice_error_angstrom": float(
                np.max(np.abs(xyz_lattice - lattice * BOHR_TO_ANGSTROM))
            ),
            "extxyz_stress_ev_per_angstrom3": xyz_stress,
            "extxyz_stress_error_gpa": float(
                np.max(np.abs(
                    xyz_stress * EV_PER_ANGSTROM3_TO_GPA - output["stress_gpa"]
                ))
            ),
        }

    # Rows in the coordinate file are lattice vectors.  The sheared basis is
    # b1=a1, b2=a1+a2, b3=a3, hence c' = U^-1 c for polarization
    # coefficients in the lattice basis.
    transform = np.asarray([[1.0, 0.0, 0.0],
                            [1.0, 1.0, 0.0],
                            [0.0, 0.0, 1.0]])
    expected_sheared = cases["base"]["coefficients"] @ np.linalg.inv(transform)
    coefficient_residual = wrapped_residual(
        cases["sheared"]["coefficients"] - expected_sheared
    )
    metrics = {
        "volume_difference_bohr3": abs(
            cases["base"]["volume_bohr3"] - cases["sheared"]["volume_bohr3"]
        ),
        "energy_difference_ha": abs(
            cases["base"]["energy_ha"] - cases["sheared"]["energy_ha"]
        ),
        "maximum_quantum_error_e_per_bohr2": max(
            case["quantum_error"] for case in cases.values()
        ),
        "maximum_polarisation_coefficient_residual_modulo_quantum": float(
            np.max(np.abs(coefficient_residual))
        ),
        "maximum_extxyz_lattice_error_angstrom": max(
            case["extxyz_lattice_error_angstrom"] for case in cases.values()
        ),
        "maximum_extxyz_stress_error_gpa": max(
            case["extxyz_stress_error_gpa"] for case in cases.values()
        ),
    }
    limits = {
        "volume_difference_bohr3": 1.0e-10,
        "energy_difference_ha": 5.0e-4,
        "maximum_quantum_error_e_per_bohr2": 5.0e-12,
        "maximum_polarisation_coefficient_residual_modulo_quantum": 5.0e-5,
        "maximum_extxyz_lattice_error_angstrom": 1.0e-7,
        "maximum_extxyz_stress_error_gpa": 2.0e-5,
    }
    failures = [key for key, value in metrics.items() if value > limits[key]]
    serializable_cases = {}
    for name, case in cases.items():
        serializable_cases[name] = {
            key: value.tolist() if isinstance(value, np.ndarray) else value
            for key, value in case.items()
        }
    summary = {
        "status": "pass" if not failures else "fail",
        "basis_transform_rows": transform.tolist(),
        "cases": serializable_cases,
        "metrics": metrics,
        "limits": limits,
        "failed_metrics": failures,
    }
    args.summary.write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    if failures:
        raise SystemExit("Polarization/extxyz validation failed: " + ", ".join(failures))


if __name__ == "__main__":
    main()
