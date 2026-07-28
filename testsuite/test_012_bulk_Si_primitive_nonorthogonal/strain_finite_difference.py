#!/usr/bin/env python3
"""Prepare and analyse all six central finite-difference strain checks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HA_BOHR3_TO_GPA = 29421.02648438959


def read_coords(filename: Path):
    lines = [line.strip() for line in filename.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    lattice = np.asarray([[float(value) for value in lines[i].split()[:3]]
                          for i in range(3)])
    atom_count = int(lines[3].split()[0])
    atoms = [lines[i].split() for i in range(4, 4 + atom_count)]
    return lattice, atoms


def write_coords(filename: Path, lattice, atoms):
    lines = [" ".join(f"{value:.14f}" for value in row) for row in lattice]
    lines.append(str(len(atoms)))
    lines.extend(" ".join(atom) for atom in atoms)
    filename.write_text("\n".join(lines) + "\n", encoding="utf-8")


def strain_basis():
    bases = {}
    for index, label in enumerate(("xx", "yy", "zz")):
        matrix = np.zeros((3, 3))
        matrix[index, index] = 1.0
        bases[label] = matrix
    for first, second, label in ((0, 1, "xy"), (0, 2, "xz"), (1, 2, "yz")):
        matrix = np.zeros((3, 3))
        matrix[first, second] = 0.5
        matrix[second, first] = 0.5
        bases[label] = matrix
    return bases


def prepare(base: Path, root: Path, delta: float):
    lattice, atoms = read_coords(base)
    # Break cubic symmetry so that all six analytic stress components are
    # nonzero and the off-diagonal implementation is genuinely tested.
    prestrain = np.asarray([
        [0.020, 0.015, -0.010],
        [0.015, -0.010, 0.012],
        [-0.010, 0.012, 0.005],
    ])
    distorted = lattice @ (np.eye(3) + prestrain).T
    points = [{"name": "base", "strain": np.zeros((3, 3)).tolist()}]
    for label, basis in strain_basis().items():
        for sign, suffix in ((-1.0, "minus"), (1.0, "plus")):
            points.append({
                "name": f"{label}_{suffix}",
                "label": label,
                "sign": int(sign),
                "strain": (sign * delta * basis).tolist(),
            })
    root.mkdir(parents=True, exist_ok=True)
    for point in points:
        directory = root / point["name"]
        directory.mkdir(parents=True, exist_ok=True)
        deformation = np.eye(3) + np.asarray(point["strain"])
        write_coords(directory / "coords.dat", distorted @ deformation.T, atoms)
    manifest = {
        "delta": delta,
        "base_volume_bohr3": abs(float(np.linalg.det(distorted))),
        "prestrain": prestrain.tolist(),
        "points": points,
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


def parse_output(filename: Path):
    text = filename.read_text(encoding="utf-8")
    energies = re.findall(r"Harris-Foulkes energy\s+=\s+([-+0-9.eE]+)", text)
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if "force: Total stress:" in line]
    if not energies or not starts:
        raise ValueError(f"Missing energy or full stress in {filename}")
    start = starts[-1]
    first = lines[start].split("force: Total stress:", 1)[1].replace("GPa", "").split()
    rows = [[float(value) for value in first[:3]]]
    rows.extend([[float(value) for value in lines[start + offset].split()[:3]]
                 for offset in (1, 2)])
    return float(energies[-1]), np.asarray(rows)


def analyse(root: Path, summary_path: Path, image: Path):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    delta = float(manifest["delta"])
    volume = float(manifest["base_volume_bohr3"])
    base_energy, stress = parse_output(root / "base" / "Conquest_out")
    results = []
    for label, basis in strain_basis().items():
        minus_energy, _ = parse_output(root / f"{label}_minus" / "Conquest_out")
        plus_energy, _ = parse_output(root / f"{label}_plus" / "Conquest_out")
        numerical = (
            (plus_energy - minus_energy) / (2.0 * delta)
            / volume * HA_BOHR3_TO_GPA
        )
        analytic = float(np.sum(stress * basis))
        results.append({
            "component": label,
            "analytic_gpa": analytic,
            "finite_difference_gpa": numerical,
            "absolute_error_gpa": abs(numerical - analytic),
            "relative_error": abs(numerical - analytic) / max(abs(analytic), 1.0e-12),
            "minus_energy_ha": minus_energy,
            "plus_energy_ha": plus_energy,
        })
    summary = {
        "strain_parameterization": (
            "normal tensor strains; engineering shear with eps_ij=eps_ji=gamma/2"
        ),
        "delta": delta,
        "base_energy_ha": base_energy,
        "base_volume_bohr3": volume,
        "analytic_stress_gpa": stress.tolist(),
        "stress_antisymmetry_max_gpa": float(np.max(np.abs(stress - stress.T))),
        "maximum_absolute_error_gpa": max(item["absolute_error_gpa"] for item in results),
        "rms_absolute_error_gpa": float(np.sqrt(np.mean([
            item["absolute_error_gpa"] ** 2 for item in results
        ]))),
        "components": results,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    labels = [item["component"] for item in results]
    positions = np.arange(len(labels))
    width = 0.38
    fig, axis = plt.subplots(figsize=(9.2, 5.4), constrained_layout=True)
    axis.bar(positions - width / 2, [item["analytic_gpa"] for item in results],
             width, label="analytic stress")
    axis.bar(positions + width / 2,
             [item["finite_difference_gpa"] for item in results],
             width, label="central energy derivative")
    axis.set_xticks(positions, labels)
    axis.set_ylabel("Stress / energy derivative (GPa)")
    axis.set_title(
        "Primitive Si in a deliberately distorted nonorthogonal cell\n"
        f"six strain derivatives; max |error| = "
        f"{summary['maximum_absolute_error_gpa']:.4f} GPa"
    )
    axis.axhline(0.0, color="#6b7280", linewidth=0.8)
    axis.grid(axis="y", color="#e5e7eb", linewidth=0.6)
    axis.legend(frameon=False)
    fig.savefig(image, dpi=180)
    plt.close(fig)
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--base", type=Path, required=True)
    prepare_parser.add_argument("--root", type=Path, required=True)
    prepare_parser.add_argument("--delta", type=float, default=5.0e-4)
    analyse_parser = subparsers.add_parser("analyse")
    analyse_parser.add_argument("--root", type=Path, required=True)
    analyse_parser.add_argument("--summary", type=Path, required=True)
    analyse_parser.add_argument("--image", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.base, args.root, args.delta)
    else:
        analyse(args.root, args.summary, args.image)


if __name__ == "__main__":
    main()
