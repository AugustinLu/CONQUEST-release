#!/usr/bin/env python3
"""Prepare and validate the published 3R graphite SFC/MPI regression."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
import spglib


ANGSTROM_TO_BOHR = 1.8897261246257702
RHOMBOHEDRAL_EDGE_ANGSTROM = 3.635
RHOMBOHEDRAL_ANGLE_DEGREES = 39.49
WYCKOFF_X = 0.164
EXPECTED_SPACE_GROUP = 166


def rhombohedral_lattice():
    """Return a row-vector rhombohedral lattice in Angstrom."""
    edge = RHOMBOHEDRAL_EDGE_ANGSTROM
    angle = math.radians(RHOMBOHEDRAL_ANGLE_DEGREES)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    lattice = np.zeros((3, 3))
    lattice[0] = (edge, 0.0, 0.0)
    lattice[1] = (edge * cosine, edge * sine, 0.0)
    lattice[2, 0] = edge * cosine
    lattice[2, 1] = edge * (cosine - cosine**2) / sine
    lattice[2, 2] = math.sqrt(
        edge**2 - lattice[2, 0]**2 - lattice[2, 1]**2
    )
    return lattice


def published_cells():
    """Build equivalent primitive rhombohedral and conventional hexagonal cells."""
    rhombohedral = rhombohedral_lattice()
    rhombohedral_positions = np.asarray([
        (WYCKOFF_X, WYCKOFF_X, WYCKOFF_X),
        (-WYCKOFF_X, -WYCKOFF_X, -WYCKOFF_X),
    ]) % 1.0

    angle = math.radians(RHOMBOHEDRAL_ANGLE_DEGREES)
    cosine = math.cos(angle)
    hexagonal_a = RHOMBOHEDRAL_EDGE_ANGSTROM * math.sqrt(
        2.0 * (1.0 - cosine)
    )
    hexagonal_c = RHOMBOHEDRAL_EDGE_ANGSTROM * math.sqrt(
        3.0 * (1.0 + 2.0 * cosine)
    )
    hexagonal = np.asarray([
        (hexagonal_a, 0.0, 0.0),
        (-0.5 * hexagonal_a, 0.5 * math.sqrt(3.0) * hexagonal_a, 0.0),
        (0.0, 0.0, hexagonal_c),
    ])
    centring = np.asarray([
        (0.0, 0.0, 0.0),
        (2.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
        (1.0 / 3.0, 2.0 / 3.0, 2.0 / 3.0),
    ])
    hexagonal_positions = np.vstack([
        (translation + np.asarray((0.0, 0.0, sign * WYCKOFF_X))) % 1.0
        for translation in centring
        for sign in (1.0, -1.0)
    ])
    return {
        "rhombohedral": (rhombohedral, rhombohedral_positions),
        "hexagonal": (hexagonal, hexagonal_positions),
    }


def write_coords(path: Path, lattice_angstrom, fractional):
    lattice_bohr = lattice_angstrom * ANGSTROM_TO_BOHR
    output = [
        " ".join(f"{value:.14f}" for value in vector)
        for vector in lattice_bohr
    ]
    output.append(str(len(fractional)))
    output.extend(
        " ".join(f"{value:.14f}" for value in position) + " 1 T T T"
        for position in fractional
    )
    path.write_text("\n".join(output) + "\n")


def symmetry_record(lattice, fractional):
    dataset = spglib.get_symmetry_dataset(
        (lattice, fractional, [6] * len(fractional)),
        symprec=1.0e-6,
    )
    if dataset is None:
        raise ValueError("spglib did not identify the published structure")
    if dataset.number != EXPECTED_SPACE_GROUP:
        raise ValueError(
            f"expected space group {EXPECTED_SPACE_GROUP}, got {dataset.number}"
        )
    return {
        "number": int(dataset.number),
        "international": dataset.international,
        "hall": dataset.hall,
    }


def prepare(root: Path):
    cells = published_cells()
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "provenance": {
            "structure": "3R rhombohedral graphite",
            "source": "Lipson and Stokes, Proc. R. Soc. A 181, 101 (1942)",
            "doi": "10.1098/rspa.1942.0063",
            "cod_id": 1200018,
        },
        "published_parameters": {
            "rhombohedral_edge_angstrom": RHOMBOHEDRAL_EDGE_ANGSTROM,
            "rhombohedral_angle_degrees": RHOMBOHEDRAL_ANGLE_DEGREES,
            "wyckoff_2c_x": WYCKOFF_X,
        },
        "representations": {},
    }
    for name, (lattice, fractional) in cells.items():
        record = {
            "atom_count": len(fractional),
            "volume_angstrom3": abs(float(np.linalg.det(lattice))),
            "volume_per_atom_angstrom3": (
                abs(float(np.linalg.det(lattice))) / len(fractional)
            ),
            "symmetry": symmetry_record(lattice, fractional),
        }
        manifest["representations"][name] = record
        for ranks in (1, 2):
            directory = root / f"{name}_np{ranks}"
            directory.mkdir(parents=True, exist_ok=True)
            write_coords(directory / "coords.dat", lattice, fractional)

    rhombohedral = manifest["representations"]["rhombohedral"]
    hexagonal = manifest["representations"]["hexagonal"]
    volume_ratio = (
        hexagonal["volume_angstrom3"] / rhombohedral["volume_angstrom3"]
    )
    if abs(volume_ratio - 3.0) > 1.0e-12:
        raise ValueError(f"hexagonal/rhombohedral volume ratio is {volume_ratio}")
    volume_per_atom_error = abs(
        hexagonal["volume_per_atom_angstrom3"]
        - rhombohedral["volume_per_atom_angstrom3"]
    )
    if volume_per_atom_error > 1.0e-12:
        raise ValueError("equivalent settings have different volume per atom")
    manifest["hexagonal_to_rhombohedral_volume_ratio"] = volume_ratio
    manifest["volume_per_atom_error_angstrom3"] = volume_per_atom_error
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def last_float(pattern: str, text: str, label: str):
    matches = re.findall(pattern, text)
    if not matches:
        raise ValueError(f"missing {label}")
    return float(matches[-1].replace("D", "E"))


def read_lattice_bohr(path: Path):
    rows = [line.split() for line in path.read_text().splitlines() if line.strip()]
    return np.asarray([[float(value) for value in row[:3]] for row in rows[:3]])


def parse_case(directory: Path, expected_atom_count: int):
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
        r"Lattice-normal spans\s+\(a0\):\s*"
        r"([-+0-9.eEdD]+)\s+([-+0-9.eEdD]+)\s+([-+0-9.eEdD]+)",
        text,
    )
    if not dimension_matches:
        raise ValueError(f"missing SFC lattice-normal spans in {directory}")
    reported_spans = np.asarray(
        [float(value.replace("D", "E")) for value in dimension_matches[-1]]
    )
    lattice = read_lattice_bohr(directory / "coords.dat")
    expected_spans = 1.0 / np.linalg.norm(np.linalg.inv(lattice), axis=0)
    span_error = float(np.max(np.abs(reported_spans - expected_spans)))

    partition_matches = re.findall(
        r"Actual N partitions in [xyz]:\s*(\d+)", text
    )
    if len(partition_matches) < 3:
        raise ValueError(f"missing partition counts in {directory}")
    partition_counts = [int(value) for value in partition_matches[-3:]]

    energy = last_float(
        r"\|\* Harris-Foulkes energy\s+=\s+([-+0-9.eEdD]+)",
        text,
        "total energy",
    )
    ewald = last_float(
        r"Ewald total energy:\s+([-+0-9.eEdD]+)", text, "Ewald energy"
    )
    maximum_force = last_float(
        r"Maximum force\s*:\s*([-+0-9.eEdD]+)", text, "maximum force"
    )
    stress_sections = text.rsplit("force: Total stress:", 1)
    if len(stress_sections) != 2:
        raise ValueError(f"missing total stress in {directory}")
    stress = [
        float(value.replace("D", "E"))
        for value in re.findall(
            r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eEdD][-+]?\d+)?",
            stress_sections[1],
        )[:9]
    ]
    values = [energy, ewald, maximum_force, *stress]
    if len(stress) != 9 or not all(math.isfinite(value) for value in values):
        raise ValueError(f"non-finite or incomplete result in {directory}")
    return {
        "atom_count": expected_atom_count,
        "sfc_system_type": system_types[-1],
        "sfc_lattice_normal_spans_bohr": reported_spans.tolist(),
        "sfc_lattice_normal_span_error_bohr": span_error,
        "partition_counts": partition_counts,
        "energy_ha": energy,
        "energy_per_atom_ha": energy / expected_atom_count,
        "ewald_ha": ewald,
        "ewald_per_atom_ha": ewald / expected_atom_count,
        "maximum_force_ha_per_bohr": maximum_force,
        "stress_gpa": stress,
    }


def analyse(root: Path):
    manifest = json.loads((root / "manifest.json").read_text())
    cases = {}
    for representation in ("rhombohedral", "hexagonal"):
        atom_count = manifest["representations"][representation]["atom_count"]
        for ranks in (1, 2):
            key = f"{representation}_np{ranks}"
            cases[key] = parse_case(root / key, atom_count)

    rank_energy_error = max(
        abs(
            cases[f"{representation}_np1"]["energy_ha"]
            - cases[f"{representation}_np2"]["energy_ha"]
        )
        for representation in ("rhombohedral", "hexagonal")
    )
    rank_ewald_error = max(
        abs(
            cases[f"{representation}_np1"]["ewald_ha"]
            - cases[f"{representation}_np2"]["ewald_ha"]
        )
        for representation in ("rhombohedral", "hexagonal")
    )
    rank_stress_error = max(
        float(np.max(np.abs(
            np.asarray(cases[f"{representation}_np1"]["stress_gpa"])
            - np.asarray(cases[f"{representation}_np2"]["stress_gpa"])
        )))
        for representation in ("rhombohedral", "hexagonal")
    )
    representation_ewald_error = max(
        abs(
            cases[f"rhombohedral_np{ranks}"]["ewald_per_atom_ha"]
            - cases[f"hexagonal_np{ranks}"]["ewald_per_atom_ha"]
        )
        for ranks in (1, 2)
    )
    lattice_normal_span_error = max(
        case["sfc_lattice_normal_span_error_bohr"] for case in cases.values()
    )
    summary = {
        "status": "pass",
        "provenance": manifest["provenance"],
        "published_parameters": manifest["published_parameters"],
        "space_group": EXPECTED_SPACE_GROUP,
        "cases": cases,
        "sfc_lattice_normal_span_error_bohr": lattice_normal_span_error,
        "rank_energy_error_ha": rank_energy_error,
        "rank_ewald_error_ha": rank_ewald_error,
        "rank_stress_error_gpa": rank_stress_error,
        "representation_ewald_per_atom_error_ha": representation_ewald_error,
    }
    limits = {
        "sfc_lattice_normal_span_error_bohr": 1.0e-5,
        "rank_energy_error_ha": 1.0e-9,
        "rank_ewald_error_ha": 1.0e-10,
        "rank_stress_error_gpa": 1.0e-8,
        "representation_ewald_per_atom_error_ha": 1.0e-9,
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
    prepare_parser.add_argument("--root", type=Path, required=True)
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.root)
    else:
        analyse(args.root)


if __name__ == "__main__":
    main()
