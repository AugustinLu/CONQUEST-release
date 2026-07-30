#!/usr/bin/env python3
"""Prepare and validate an extreme-skew SFC/MPI regression."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np


# 2026/07/29 lu
# Row-vector convention: lattice' = U lattice and fractional' = fractional U^-1.
TRANSFORM = np.asarray([[1, 0, 0], [8, 1, 0], [0, 0, 1]], dtype=int)


def read_coords(path: Path):
    lines = [line.split() for line in path.read_text().splitlines() if line.strip()]
    lattice = np.asarray([[float(value) for value in row[:3]] for row in lines[:3]])
    count = int(lines[3][0])
    atoms = lines[4:4 + count]
    fractional = np.asarray([[float(value) for value in row[:3]] for row in atoms])
    suffixes = [row[3:] for row in atoms]
    return lattice, fractional, suffixes


def write_coords(path: Path, lattice, fractional, suffixes):
    output = [" ".join(f"{value:.14f}" for value in row) for row in lattice]
    output.append(str(len(suffixes)))
    for position, suffix in zip(fractional, suffixes, strict=True):
        output.append(
            " ".join(f"{value:.14f}" for value in position)
            + " " + " ".join(suffix)
        )
    path.write_text("\n".join(output) + "\n")


def prepare(source: Path, root: Path):
    lattice, fractional, suffixes = read_coords(source)
    inverse = np.linalg.inv(TRANSFORM)
    skew_lattice = TRANSFORM @ lattice
    skew_fractional = fractional @ inverse
    position_error = float(np.max(np.abs(
        fractional @ lattice - skew_fractional @ skew_lattice
    )))
    volume_error = abs(float(
        np.linalg.det(lattice) - np.linalg.det(skew_lattice)
    ))
    if position_error > 1.0e-12 or volume_error > 1.0e-10:
        raise ValueError("generated cells are not exactly equivalent")

    for representation, cell, positions in (
        ("reduced", lattice, fractional),
        ("extreme", skew_lattice, skew_fractional),
    ):
        for ranks in (1, 2):
            directory = root / f"{representation}_np{ranks}"
            directory.mkdir(parents=True, exist_ok=True)
            write_coords(directory / "coords.dat", cell, positions, suffixes)

    manifest = {
        "transform": TRANSFORM.tolist(),
        "transform_determinant": int(round(np.linalg.det(TRANSFORM))),
        "maximum_cartesian_position_error_bohr": position_error,
        "volume_error_bohr3": volume_error,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def last_float(pattern: str, text: str, label: str):
    matches = re.findall(pattern, text)
    if not matches:
        raise ValueError(f"missing {label}")
    return float(matches[-1].replace("D", "E"))


def parse_case(directory: Path):
    text = (directory / "Conquest_out").read_text()
    if "Reached SCF tolerance" not in text:
        raise ValueError(f"SCF did not converge in {directory}")
    partition = directory / "hilbert_make_blk.dat"
    if not partition.is_file() or partition.stat().st_size == 0:
        raise ValueError(f"missing Hilbert SFC partition in {directory}")

    system_types = re.findall(r"Detected system type:\s*(\w+)", text)
    if not system_types or system_types[-1] != "bulk":
        raise ValueError(f"expected bulk SFC classification in {directory}")
    dimension_matches = re.findall(
        r"(?:Cell dimensions|Lattice dimensions|Lattice-normal spans)"
        r"\s+\(a0\):\s*"
        r"([-+0-9.eEdD]+)\s+([-+0-9.eEdD]+)\s+([-+0-9.eEdD]+)",
        text,
    )
    if not dimension_matches:
        raise ValueError(f"missing SFC lattice dimensions in {directory}")
    reported_dimensions = np.asarray(
        [float(value.replace("D", "E")) for value in dimension_matches[-1]]
    )
    lattice, _, _ = read_coords(directory / "coords.dat")
    expected_dimensions = 1.0 / np.linalg.norm(
        np.linalg.inv(lattice), axis=0
    )
    dimension_error = float(np.max(np.abs(
        reported_dimensions - expected_dimensions
    )))

    energy = last_float(
        r"\|\* Harris-Foulkes energy\s+=\s+([-+0-9.eEdD]+)",
        text, "total energy")
    ewald = last_float(
        r"Ewald total energy:\s+([-+0-9.eEdD]+)", text, "Ewald energy")
    maximum_force = last_float(
        r"Maximum force\s*:\s*([-+0-9.eEdD]+)", text, "maximum force")
    stress_sections = text.rsplit("force: Total stress:", 1)
    if len(stress_sections) != 2:
        raise ValueError(f"missing total stress in {directory}")
    stress_values = [
        float(value)
        for value in re.findall(
            r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eEdD][-+]?\d+)?",
            stress_sections[1])[:9]
    ]
    values = [energy, ewald, maximum_force, *stress_values]
    if len(stress_values) != 9 or not all(math.isfinite(value) for value in values):
        raise ValueError(f"non-finite or incomplete result in {directory}")
    return {
        "sfc_system_type": system_types[-1],
        "sfc_lattice_normal_spans_bohr": reported_dimensions.tolist(),
        "sfc_lattice_normal_span_error_bohr": dimension_error,
        "energy_ha": energy,
        "ewald_ha": ewald,
        "maximum_force_ha_per_bohr": maximum_force,
        "stress_gpa": stress_values,
    }


def analyse(root: Path):
    cases = {
        f"{representation}_np{ranks}":
            parse_case(root / f"{representation}_np{ranks}")
        for representation in ("reduced", "extreme")
        for ranks in (1, 2)
    }
    rank_energy_error = max(
        abs(cases[f"{name}_np1"]["energy_ha"] - cases[f"{name}_np2"]["energy_ha"])
        for name in ("reduced", "extreme")
    )
    rank_ewald_error = max(
        abs(cases[f"{name}_np1"]["ewald_ha"] - cases[f"{name}_np2"]["ewald_ha"])
        for name in ("reduced", "extreme")
    )
    basis_ewald_error = max(
        abs(cases[f"reduced_np{ranks}"]["ewald_ha"]
            - cases[f"extreme_np{ranks}"]["ewald_ha"])
        for ranks in (1, 2)
    )
    lattice_normal_span_error = max(
        case["sfc_lattice_normal_span_error_bohr"] for case in cases.values()
    )
    summary = {
        "status": "pass",
        "cases": cases,
        "sfc_lattice_normal_span_error_bohr": lattice_normal_span_error,
        "rank_energy_error_ha": rank_energy_error,
        "rank_ewald_error_ha": rank_ewald_error,
        "basis_ewald_error_ha": basis_ewald_error,
    }
    limits = {
        "sfc_lattice_normal_span_error_bohr": 1.0e-5,
        "rank_energy_error_ha": 1.0e-9,
        "rank_ewald_error_ha": 1.0e-10,
        "basis_ewald_error_ha": 1.0e-9,
    }
    failures = [key for key, limit in limits.items() if summary[key] > limit]
    if failures:
        summary["status"] = "fail"
        summary["failed_metrics"] = failures
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if failures:
        raise SystemExit("failed: " + ", ".join(failures))


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--source", type=Path, required=True)
    prepare_parser.add_argument("--root", type=Path, required=True)
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.source, args.root)
    else:
        analyse(args.root)


if __name__ == "__main__":
    main()
