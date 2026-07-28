#!/usr/bin/env python3
"""Prepare and analyse six Ewald stress finite differences for monoclinic HfO2."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HA_BOHR3_TO_GPA = 29421.02648438959


def read_coords(filename: Path):
    lines = [
        line.strip()
        for line in filename.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    lattice = np.asarray(
        [[float(value) for value in lines[index].split()[:3]] for index in range(3)]
    )
    atom_count = int(lines[3].split()[0])
    atoms = [lines[index].split() for index in range(4, 4 + atom_count)]
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
    # The experimental monoclinic cell already tests xz coupling.  A small
    # symmetric prestrain breaks its remaining mirror/axis cancellations so
    # that xy and yz are nonzero acceptance checks too.
    prestrain = np.asarray(
        [
            [0.008, 0.006, -0.004],
            [0.006, -0.005, 0.005],
            [-0.004, 0.005, 0.003],
        ]
    )
    distorted = lattice @ (np.eye(3) + prestrain).T
    points = [{"name": "base", "strain": np.zeros((3, 3)).tolist()}]
    for label, basis in strain_basis().items():
        for sign, suffix in ((-1.0, "minus"), (1.0, "plus")):
            points.append(
                {
                    "name": f"{label}_{suffix}",
                    "label": label,
                    "sign": int(sign),
                    "strain": (sign * delta * basis).tolist(),
                }
            )
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
    energies = re.findall(r"DFT total energy\s+=\s+([-+0-9.eE]+)", text)
    ewald_energies = re.findall(
        r"Ewald total energy:\s+([-+0-9.eE]+)", text
    )
    lines = text.splitlines()
    starts = [
        index for index, line in enumerate(lines) if "force: Total stress:" in line
    ]
    if not energies or not ewald_energies or not starts:
        raise ValueError(
            f"Missing DFT energy, Ewald energy or full stress in {filename}"
        )

    def read_stress(start, label):
        first = lines[start].split(label, 1)[1].replace("GPa", "").split()
        rows = [[float(value) for value in first[:3]]]
        rows.extend(
            [
                [float(value) for value in lines[start + offset].split()[:3]]
                for offset in (1, 2)
            ]
        )
        return np.asarray(rows)

    ion_starts = [
        index for index, line in enumerate(lines) if "force: Ion-ion stress:" in line
    ]
    return {
        "energy": float(energies[-1]),
        "stress": read_stress(starts[-1], "force: Total stress:"),
        "ewald_energy": float(ewald_energies[-1]),
        "ion_stress": (
            read_stress(ion_starts[-1], "force: Ion-ion stress:")
            if ion_starts
            else None
        ),
    }


def analyse(
    root: Path,
    summary_path: Path,
    image: Path,
    ewald_tolerance_gpa: float | None,
):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    delta = float(manifest["delta"])
    volume = float(manifest["base_volume_bohr3"])
    base = parse_output(root / "base" / "Conquest_out")
    base_energy = base["energy"]
    stress = base["stress"]
    ion_stress = base["ion_stress"]
    if ion_stress is None:
        raise ValueError(
            "The base output must include the ion-ion stress; use IO.Iprint 3"
        )
    results = []
    for label, basis in strain_basis().items():
        minus = parse_output(root / f"{label}_minus" / "Conquest_out")
        plus = parse_output(root / f"{label}_plus" / "Conquest_out")
        minus_energy = minus["energy"]
        plus_energy = plus["energy"]
        numerical = (
            (plus_energy - minus_energy)
            / (2.0 * delta)
            / volume
            * HA_BOHR3_TO_GPA
        )
        analytic = float(np.sum(stress * basis))
        ewald_numerical = (
            (plus["ewald_energy"] - minus["ewald_energy"])
            / (2.0 * delta)
            / volume
            * HA_BOHR3_TO_GPA
        )
        ewald_analytic = float(np.sum(ion_stress * basis))
        results.append(
            {
                "component": label,
                "analytic_gpa": analytic,
                "finite_difference_gpa": numerical,
                "absolute_error_gpa": abs(numerical - analytic),
                "relative_error": abs(numerical - analytic)
                / max(abs(analytic), 1.0e-12),
                "ewald_analytic_gpa": ewald_analytic,
                "ewald_finite_difference_gpa": ewald_numerical,
                "ewald_absolute_error_gpa": abs(ewald_numerical - ewald_analytic),
                "ewald_relative_error": abs(ewald_numerical - ewald_analytic)
                / max(abs(ewald_analytic), 1.0e-12),
                "minus_energy_ha": minus_energy,
                "plus_energy_ha": plus_energy,
                "minus_ewald_energy_ha": minus["ewald_energy"],
                "plus_ewald_energy_ha": plus["ewald_energy"],
            }
        )
    summary = {
        "electrostatics": "explicit ionic Ewald (General.NeutralAtom F)",
        "strain_parameterization": (
            "normal tensor strains; engineering shear with eps_ij=eps_ji=gamma/2"
        ),
        "delta": delta,
        "base_energy_ha": base_energy,
        "base_volume_bohr3": volume,
        "analytic_stress_gpa": stress.tolist(),
        "analytic_ion_ion_stress_gpa": ion_stress.tolist(),
        "stress_antisymmetry_max_gpa": float(np.max(np.abs(stress - stress.T))),
        "maximum_absolute_error_gpa": max(
            item["absolute_error_gpa"] for item in results
        ),
        "rms_absolute_error_gpa": float(
            np.sqrt(np.mean([item["absolute_error_gpa"] ** 2 for item in results]))
        ),
        "ewald_maximum_absolute_error_gpa": max(
            item["ewald_absolute_error_gpa"] for item in results
        ),
        "ewald_rms_absolute_error_gpa": float(
            np.sqrt(
                np.mean([item["ewald_absolute_error_gpa"] ** 2 for item in results])
            )
        ),
        "components": results,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    labels = [item["component"] for item in results]
    positions = np.arange(len(labels))
    width = 0.38
    figure, axes = plt.subplots(1, 2, figsize=(13.2, 5.4), constrained_layout=True)
    axes[0].bar(
        positions - width / 2,
        [item["analytic_gpa"] for item in results],
        width,
        label="analytic stress",
    )
    axes[0].bar(
        positions + width / 2,
        [item["finite_difference_gpa"] for item in results],
        width,
        label="central energy derivative",
    )
    axes[0].set_title(
        "Total DFT stress\n"
        f"max |error| = {summary['maximum_absolute_error_gpa']:.4f} GPa"
    )
    axes[1].bar(
        positions - width / 2,
        [item["ewald_analytic_gpa"] for item in results],
        width,
        label="analytic ion-ion stress",
    )
    axes[1].bar(
        positions + width / 2,
        [item["ewald_finite_difference_gpa"] for item in results],
        width,
        label="Ewald energy derivative",
    )
    axes[1].set_title(
        "Ionic Ewald contribution\n"
        f"max |error| = {summary['ewald_maximum_absolute_error_gpa']:.4f} GPa"
    )
    for axis in axes:
        axis.set_xticks(positions, labels)
        axis.set_ylabel("Stress / energy derivative (GPa)")
        axis.axhline(0.0, color="#6b7280", linewidth=0.8)
        axis.grid(axis="y", color="#e5e7eb", linewidth=0.6)
        axis.legend(frameon=False)
    figure.suptitle("Monoclinic HfO2 six-strain validation")
    figure.savefig(image, dpi=180)
    plt.close(figure)
    print(json.dumps(summary, indent=2))
    if (
        ewald_tolerance_gpa is not None
        and summary["ewald_maximum_absolute_error_gpa"] > ewald_tolerance_gpa
    ):
        raise SystemExit(
            "Ewald stress validation failed: maximum error "
            f"{summary['ewald_maximum_absolute_error_gpa']:.6f} GPa exceeds "
            f"{ewald_tolerance_gpa:.6f} GPa"
        )


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
    analyse_parser.add_argument("--ewald-tolerance-gpa", type=float)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.base, args.root, args.delta)
    else:
        analyse(
            args.root,
            args.summary,
            args.image,
            args.ewald_tolerance_gpa,
        )


if __name__ == "__main__":
    main()
