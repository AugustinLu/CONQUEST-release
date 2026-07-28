#!/usr/bin/env python3
"""Prepare and analyse equivalent-cell and MPI-rank invariance checks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np


UNIMODULAR_TRANSFORM = np.asarray(
    [
        [1, 0, 0],
        [1, 1, 0],
        [0, 0, 1],
    ],
    dtype=int,
)


def read_coords(filename: Path):
    lines = [
        line.strip()
        for line in filename.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    lattice = np.asarray(
        [[float(value) for value in lines[index].split()[:3]]
         for index in range(3)]
    )
    atom_count = int(lines[3].split()[0])
    atoms = [lines[index].split() for index in range(4, 4 + atom_count)]
    fractional = np.asarray(
        [[float(value) for value in atom[:3]] for atom in atoms]
    )
    species = [atom[3] for atom in atoms]
    return lattice, fractional, species


def write_coords(filename: Path, lattice, fractional, species):
    lines = [" ".join(f"{value:.14f}" for value in row) for row in lattice]
    lines.append(str(len(species)))
    for position, atom_species in zip(fractional, species, strict=True):
        lines.append(
            " ".join(f"{value:.14f}" for value in position)
            + f" {atom_species} T T T"
        )
    filename.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare(base: Path, root: Path):
    lattice, fractional, species = read_coords(base)
    transform = UNIMODULAR_TRANSFORM
    inverse = np.linalg.inv(transform)
    transformed_lattice = transform @ lattice
    transformed_fractional = fractional @ inverse

    base_cartesian = fractional @ lattice
    transformed_cartesian = transformed_fractional @ transformed_lattice
    cartesian_error = float(
        np.max(np.abs(base_cartesian - transformed_cartesian))
    )
    volume_error = abs(
        float(np.linalg.det(lattice))
        - float(np.linalg.det(transformed_lattice))
    )
    if cartesian_error > 1.0e-12 or volume_error > 1.0e-10:
        raise ValueError("The generated cell is not physically equivalent")

    root.mkdir(parents=True, exist_ok=True)
    for representation, cell, positions in (
        ("base", lattice, fractional),
        ("sheared", transformed_lattice, transformed_fractional),
    ):
        for ranks in (1, 2):
            directory = root / f"{representation}_np{ranks}"
            directory.mkdir(parents=True, exist_ok=True)
            write_coords(directory / "coords.dat", cell, positions, species)

    manifest = {
        "unimodular_transform": transform.tolist(),
        "determinant": int(round(np.linalg.det(transform))),
        "base_volume_bohr3": abs(float(np.linalg.det(lattice))),
        "transformed_volume_bohr3": abs(
            float(np.linalg.det(transformed_lattice))
        ),
        "maximum_cartesian_position_error_bohr": cartesian_error,
        "cases": [
            {"name": f"{representation}_np{ranks}",
             "representation": representation, "mpi_ranks": ranks}
            for representation in ("base", "sheared")
            for ranks in (1, 2)
        ],
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


def parse_output(filename: Path):
    text = filename.read_text(encoding="utf-8")
    energies = re.findall(
        r"\|\* Harris-Foulkes energy\s+=\s+([-+0-9.eEdD]+)", text
    )
    ewald = re.findall(
        r"Ewald total energy:\s+([-+0-9.eEdD]+)", text
    )
    lines = text.splitlines()

    force_starts = [
        index for index, line in enumerate(lines)
        if "force: Forces on atoms (Ha/a0)" in line
    ]
    stress_starts = [
        index for index, line in enumerate(lines)
        if "force: Total stress:" in line
    ]
    if not energies or not ewald or not force_starts or not stress_starts:
        raise ValueError(f"Missing energy, Ewald, force, or stress in {filename}")

    force_start = force_starts[-1]
    forces = []
    compact_force_pattern = re.compile(
        r"force:\s+\d+\s+([-+0-9.eEdD]+)\s+"
        r"([-+0-9.eEdD]+)\s+([-+0-9.eEdD]+)"
    )
    detailed_force_pattern = re.compile(
        r"force: Force Total\s+:\s+([-+0-9.eEdD]+)\s+"
        r"([-+0-9.eEdD]+)\s+([-+0-9.eEdD]+)"
    )
    for line in lines[force_start + 1:]:
        match = compact_force_pattern.search(line)
        if not match:
            match = detailed_force_pattern.search(line)
        if match:
            forces.append([float(value.replace("D", "E")) for value in match.groups()])
        elif forces and "Maximum force" in line:
            break

    stress_start = stress_starts[-1]
    first = (
        lines[stress_start]
        .split("force: Total stress:", 1)[1]
        .replace("GPa", "")
        .split()
    )
    stress = [[float(value) for value in first[:3]]]
    stress.extend(
        [[float(value) for value in lines[stress_start + offset].split()[:3]]
         for offset in (1, 2)]
    )
    if not forces:
        raise ValueError(f"Could not parse forces from {filename}")
    return {
        "total_energy_ha": float(energies[-1].replace("D", "E")),
        "ewald_energy_ha": float(ewald[-1].replace("D", "E")),
        "forces_ha_per_bohr": np.asarray(forces),
        "stress_gpa": np.asarray(stress),
    }


def comparison(left_name, right_name, cases):
    left = cases[left_name]
    right = cases[right_name]
    return {
        "left": left_name,
        "right": right_name,
        "total_energy_difference_ha": abs(
            left["total_energy_ha"] - right["total_energy_ha"]
        ),
        "ewald_energy_difference_ha": abs(
            left["ewald_energy_ha"] - right["ewald_energy_ha"]
        ),
        "maximum_force_component_difference_ha_per_bohr": float(
            np.max(np.abs(
                left["forces_ha_per_bohr"] - right["forces_ha_per_bohr"]
            ))
        ),
        "maximum_stress_component_difference_gpa": float(
            np.max(np.abs(left["stress_gpa"] - right["stress_gpa"]))
        ),
    }


def analyse(root: Path, summary_path: Path, args):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    parsed = {
        item["name"]: parse_output(root / item["name"] / "Conquest_out")
        for item in manifest["cases"]
    }
    comparisons = {
        "basis_np1": comparison("base_np1", "sheared_np1", parsed),
        "basis_np2": comparison("base_np2", "sheared_np2", parsed),
        "rank_base": comparison("base_np1", "base_np2", parsed),
        "rank_sheared": comparison("sheared_np1", "sheared_np2", parsed),
    }

    basis_checks = [comparisons["basis_np1"], comparisons["basis_np2"]]
    rank_checks = [comparisons["rank_base"], comparisons["rank_sheared"]]
    limits = {
        "basis_energy_ha": args.basis_energy_tolerance,
        "basis_ewald_ha": args.basis_ewald_tolerance,
        "basis_force_ha_per_bohr": args.basis_force_tolerance,
        "basis_stress_gpa": args.basis_stress_tolerance,
        "rank_energy_ha": args.rank_energy_tolerance,
        "rank_ewald_ha": args.rank_ewald_tolerance,
        "rank_force_ha_per_bohr": args.rank_force_tolerance,
        "rank_stress_gpa": args.rank_stress_tolerance,
    }
    observed = {
        "basis_energy_ha": max(
            item["total_energy_difference_ha"] for item in basis_checks
        ),
        "basis_ewald_ha": max(
            item["ewald_energy_difference_ha"] for item in basis_checks
        ),
        "basis_force_ha_per_bohr": max(
            item["maximum_force_component_difference_ha_per_bohr"]
            for item in basis_checks
        ),
        "basis_stress_gpa": max(
            item["maximum_stress_component_difference_gpa"]
            for item in basis_checks
        ),
        "rank_energy_ha": max(
            item["total_energy_difference_ha"] for item in rank_checks
        ),
        "rank_ewald_ha": max(
            item["ewald_energy_difference_ha"] for item in rank_checks
        ),
        "rank_force_ha_per_bohr": max(
            item["maximum_force_component_difference_ha_per_bohr"]
            for item in rank_checks
        ),
        "rank_stress_gpa": max(
            item["maximum_stress_component_difference_gpa"]
            for item in rank_checks
        ),
    }
    failures = [
        key for key, value in observed.items() if value > limits[key]
    ]

    serializable_cases = {}
    for name, case in parsed.items():
        serializable_cases[name] = {
            "total_energy_ha": case["total_energy_ha"],
            "ewald_energy_ha": case["ewald_energy_ha"],
            "maximum_force_ha_per_bohr": float(
                np.max(np.abs(case["forces_ha_per_bohr"]))
            ),
            "stress_gpa": case["stress_gpa"].tolist(),
        }
    summary = {
        "status": "pass" if not failures else "fail",
        "manifest": manifest,
        "cases": serializable_cases,
        "comparisons": comparisons,
        "observed_maxima": observed,
        "acceptance_limits": limits,
        "failed_metrics": failures,
    }
    summary_path.write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    if failures:
        raise SystemExit(
            "Equivalent-cell invariance failed: " + ", ".join(failures)
        )


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--base", type=Path, required=True)
    prepare_parser.add_argument("--root", type=Path, required=True)

    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--root", type=Path, required=True)
    analyse_parser.add_argument("--summary", type=Path, required=True)
    analyse_parser.add_argument("--basis-energy-tolerance", type=float, default=1.0e-4)
    analyse_parser.add_argument("--basis-ewald-tolerance", type=float, default=1.0e-9)
    analyse_parser.add_argument("--basis-force-tolerance", type=float, default=5.0e-4)
    analyse_parser.add_argument("--basis-stress-tolerance", type=float, default=0.10)
    analyse_parser.add_argument("--rank-energy-tolerance", type=float, default=1.0e-9)
    analyse_parser.add_argument("--rank-ewald-tolerance", type=float, default=1.0e-10)
    analyse_parser.add_argument("--rank-force-tolerance", type=float, default=1.0e-8)
    analyse_parser.add_argument("--rank-stress-tolerance", type=float, default=1.0e-6)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.base, args.root)
    else:
        analyse(args.root, args.summary, args)


if __name__ == "__main__":
    main()
