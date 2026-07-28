#!/usr/bin/env python3
"""Prepare and fit a hydrostatic third-order Birch-Murnaghan Si EOS."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit


BOHR_TO_ANGSTROM = 0.529177210903
HA_BOHR3_TO_GPA = 29421.02648438959
HA_TO_EV = 27.211386245988


def read_coords(filename: Path):
    lines = [line.strip() for line in filename.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    lattice = np.asarray([[float(value) for value in lines[i].split()[:3]]
                          for i in range(3)])
    atom_count = int(lines[3].split()[0])
    atoms = [lines[i].split() for i in range(4, 4 + atom_count)]
    return lattice, atoms


def prepare(base: Path, root: Path, volume_ratios):
    lattice, atoms = read_coords(base)
    base_volume = abs(float(np.linalg.det(lattice)))
    points = []
    root.mkdir(parents=True, exist_ok=True)
    for ratio in volume_ratios:
        linear_scale = ratio ** (1.0 / 3.0)
        directory = root / f"volume_{ratio:.3f}"
        directory.mkdir(parents=True, exist_ok=True)
        scaled = lattice * linear_scale
        lines = [" ".join(f"{value:.12f}" for value in row) for row in scaled]
        lines.append(str(len(atoms)))
        lines.extend(" ".join(atom) for atom in atoms)
        (directory / "coords.dat").write_text("\n".join(lines) + "\n", encoding="utf-8")
        points.append({
            "volume_ratio": ratio,
            "linear_scale": linear_scale,
            "volume_bohr3": base_volume * ratio,
            "directory": directory.name,
        })
    manifest = {
        "base_coordinates": str(base),
        "base_volume_bohr3": base_volume,
        "points": points,
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


def birch_murnaghan_energy(volume, energy0, volume0, bulk0, bulk_prime):
    eta2 = (volume0 / volume) ** (2.0 / 3.0)
    strain = eta2 - 1.0
    return energy0 + (9.0 * volume0 * bulk0 / 16.0) * (
        bulk_prime * strain**3 + (6.0 - 4.0 * eta2) * strain**2
    )


def birch_murnaghan_pressure(volume, volume0, bulk0, bulk_prime):
    eta = (volume0 / volume) ** (1.0 / 3.0)
    return 1.5 * bulk0 * (eta**7 - eta**5) * (
        1.0 + 0.75 * (bulk_prime - 4.0) * (eta**2 - 1.0)
    )


def parse_output(filename: Path):
    text = filename.read_text(encoding="utf-8")
    energy_matches = re.findall(r"Harris-Foulkes energy\s+=\s+([-+0-9.eE]+)", text)
    stress_matches = re.findall(
        r"Total stress:\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)",
        text,
    )
    if not energy_matches or not stress_matches:
        raise ValueError(f"Missing energy or stress in {filename}")
    diagonal_stress = np.asarray([float(value) for value in stress_matches[-1]])
    return float(energy_matches[-1]), float(diagonal_stress.mean()), diagonal_stress


def fit(root: Path, image: Path, summary_path: Path):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    points = []
    for point in manifest["points"]:
        directory = root / point["directory"]
        lattice, atoms = read_coords(directory / "coords.dat")
        energy, mean_stress, diagonal_stress = parse_output(directory / "Conquest_out")
        points.append({
            **point,
            "volume_bohr3": abs(float(np.linalg.det(lattice))),
            "atom_count": len(atoms),
            "energy_ha": energy,
            "reported_mean_stress_gpa": mean_stress,
            "reported_diagonal_stress_gpa": diagonal_stress.tolist(),
        })
    points.sort(key=lambda item: item["volume_bohr3"])
    volumes = np.asarray([point["volume_bohr3"] for point in points])
    energies = np.asarray([point["energy_ha"] for point in points])
    stresses = np.asarray([point["reported_mean_stress_gpa"] for point in points])

    minimum = int(np.argmin(energies))
    initial = [energies[minimum], volumes[minimum], 100.0 / HA_BOHR3_TO_GPA, 4.0]
    bounds = (
        [energies.min() - 1.0, volumes.min(), 1.0e-6, 0.0],
        [energies.min() + 1.0, volumes.max(), 0.1, 12.0],
    )
    parameters, covariance = curve_fit(
        birch_murnaghan_energy, volumes, energies, p0=initial,
        bounds=bounds, maxfev=50000,
    )
    energy0, volume0, bulk0, bulk_prime = parameters
    fit_energies = birch_murnaghan_energy(volumes, *parameters)
    rmse_mev_per_atom = (
        float(np.sqrt(np.mean((fit_energies - energies) ** 2)))
        * HA_TO_EV * 1000.0 / points[0]["atom_count"]
    )
    fit_pressures = (
        birch_murnaghan_pressure(volumes, volume0, bulk0, bulk_prime)
        * HA_BOHR3_TO_GPA
    )
    same_sign_rmse = float(np.sqrt(np.mean((stresses - fit_pressures) ** 2)))
    opposite_sign_rmse = float(np.sqrt(np.mean((stresses + fit_pressures) ** 2)))
    stress_sign = 1 if same_sign_rmse <= opposite_sign_rmse else -1
    stress_rmse = min(same_sign_rmse, opposite_sign_rmse)

    dense_volumes = np.linspace(volumes.min(), volumes.max(), 500)
    dense_energies = birch_murnaghan_energy(dense_volumes, *parameters)
    dense_pressures = (
        birch_murnaghan_pressure(dense_volumes, volume0, bulk0, bulk_prime)
        * HA_BOHR3_TO_GPA
    )
    atoms = points[0]["atom_count"]

    fig, (energy_ax, pressure_ax) = plt.subplots(
        1, 2, figsize=(12.5, 5.6), constrained_layout=True
    )
    reference_energy = energy0
    energy_ax.scatter(
        volumes / atoms,
        (energies - reference_energy) * HA_TO_EV * 1000.0 / atoms,
        color="#155e75", label="CONQUEST",
    )
    energy_ax.plot(
        dense_volumes / atoms,
        (dense_energies - reference_energy) * HA_TO_EV * 1000.0 / atoms,
        color="#d97706", label="Birch-Murnaghan fit",
    )
    energy_ax.axvline(volume0 / atoms, color="#6b7280", linestyle="--", linewidth=0.9)
    energy_ax.set_xlabel(r"Volume per atom (bohr$^3$)")
    energy_ax.set_ylabel("Energy relative to fitted minimum (meV/atom)")
    energy_ax.legend(frameon=False)
    energy_ax.grid(color="#e5e7eb", linewidth=0.6)

    pressure_ax.scatter(
        volumes / atoms, stress_sign * stresses, color="#155e75",
        label=f"CONQUEST stress x {stress_sign:+d}",
    )
    pressure_ax.plot(
        dense_volumes / atoms, dense_pressures, color="#d97706",
        label="EOS pressure",
    )
    pressure_ax.axhline(0.0, color="#6b7280", linewidth=0.8)
    pressure_ax.axvline(volume0 / atoms, color="#6b7280", linestyle="--", linewidth=0.9)
    pressure_ax.set_xlabel(r"Volume per atom (bohr$^3$)")
    pressure_ax.set_ylabel("Pressure (GPa)")
    pressure_ax.legend(frameon=False)
    pressure_ax.grid(color="#e5e7eb", linewidth=0.6)

    conventional_a_bohr = (4.0 * volume0) ** (1.0 / 3.0)
    fig.suptitle(
        "Primitive diamond Si - third-order Birch-Murnaghan equation of state\n"
        f"$a_0$ = {conventional_a_bohr * BOHR_TO_ANGSTROM:.4f} A; "
        f"$B_0$ = {bulk0 * HA_BOHR3_TO_GPA:.2f} GPa; "
        f"$B'_0$ = {bulk_prime:.3f}; fit RMSE = {rmse_mev_per_atom:.4f} meV/atom",
        fontsize=14,
    )
    image.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(image, dpi=180)
    plt.close(fig)

    summary = {
        "model": "third-order Birch-Murnaghan",
        "point_count": len(points),
        "equilibrium_energy_ha": float(energy0),
        "equilibrium_primitive_volume_bohr3": float(volume0),
        "equilibrium_volume_per_atom_bohr3": float(volume0 / atoms),
        "equilibrium_conventional_lattice_bohr": float(conventional_a_bohr),
        "equilibrium_conventional_lattice_angstrom": float(
            conventional_a_bohr * BOHR_TO_ANGSTROM
        ),
        "bulk_modulus_ha_per_bohr3": float(bulk0),
        "bulk_modulus_gpa": float(bulk0 * HA_BOHR3_TO_GPA),
        "bulk_modulus_derivative": float(bulk_prime),
        "energy_fit_rmse_mev_per_atom": rmse_mev_per_atom,
        "reported_stress_to_pressure_sign": stress_sign,
        "pressure_stress_rmse_gpa": stress_rmse,
        "parameter_standard_errors": np.sqrt(np.diag(covariance)).tolist(),
        "points": points,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--base", type=Path, required=True)
    prepare_parser.add_argument("--root", type=Path, required=True)
    prepare_parser.add_argument(
        "--volume-ratios", type=float, nargs="+",
        default=[0.92, 0.94, 0.96, 0.98, 1.00, 1.02, 1.04, 1.06, 1.08],
    )
    fit_parser = subparsers.add_parser("fit")
    fit_parser.add_argument("--root", type=Path, required=True)
    fit_parser.add_argument("--image", type=Path, required=True)
    fit_parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "prepare":
        prepare(args.base, args.root, args.volume_ratios)
    else:
        fit(args.root, args.image, args.summary)


if __name__ == "__main__":
    main()
