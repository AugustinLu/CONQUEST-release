#!/usr/bin/env python3
"""Plot primitive-Si bands and l-resolved pDOS and write validation metrics."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HARTREE_TO_EV = 27.211386245988


def numeric_rows(filename: Path) -> np.ndarray:
    rows = []
    for line in filename.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "&":
            continue
        try:
            rows.append([float(value) for value in stripped.split()])
        except ValueError:
            continue
    return np.asarray(rows)


def read_eigenvalues(filename: Path):
    lines = filename.read_text(encoding="utf-8").splitlines()
    header = re.search(r"#\s+(\d+)\s+eigenvalues\s+(\d+)\s+kpoints", lines[0])
    fermi_match = re.search(r"Ef:\s+([-+0-9.eE]+)", lines[1])
    if not header or not fermi_match:
        raise ValueError(f"Cannot parse {filename}")
    bands, kpoints = map(int, header.groups())
    kcoords = np.empty((kpoints, 3))
    eigenvalues = np.empty((kpoints, bands))
    cursor = 3
    for ikpt in range(kpoints):
        while not lines[cursor].strip():
            cursor += 1
        fields = lines[cursor].split()
        cursor += 1
        kcoords[ikpt] = [float(value) for value in fields[1:4]]
        for iband in range(bands):
            eigenvalues[ikpt, iband] = float(lines[cursor].split()[1])
            cursor += 1
    return kcoords, eigenvalues, float(fermi_match.group(1))


def reciprocal_rows(coords: Path) -> np.ndarray:
    lattice = np.loadtxt(coords, max_rows=3)
    return np.linalg.inv(lattice).T


def read_fractional_basis(coords: Path):
    lines = [line.strip() for line in coords.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    lattice = np.asarray([[float(value) for value in lines[i].split()[:3]]
                          for i in range(3)])
    atom_count = int(lines[3].split()[0])
    positions = np.asarray([[float(value) for value in lines[i].split()[:3]]
                            for i in range(4, 4 + atom_count)])
    return lattice, positions


def diamond_basis_error(coords: Path) -> float:
    lattice, positions = read_fractional_basis(coords)
    relative = np.mod(positions[1] - positions[0], 1.0)
    fractional_error = relative - np.asarray([0.25, 0.25, 0.25])
    fractional_error -= np.rint(fractional_error)
    return float(np.linalg.norm(fractional_error @ lattice))


def force_history(conquest_output: Path):
    pattern = re.compile(r"Maximum force\s+:\s+([-+0-9.eE]+)")
    return [float(match.group(1)) for match in
            pattern.finditer(conquest_output.read_text(encoding="utf-8"))]


def segment_indices(path, points_per_segment: int):
    segments = []
    cursor = 0
    previous_end = None
    for start, end in path:
        if start == previous_end:
            indices = np.arange(cursor - 1, cursor + points_per_segment - 1)
            cursor += points_per_segment - 1
        else:
            indices = np.arange(cursor, cursor + points_per_segment)
            cursor += points_per_segment
        segments.append((start, end, indices))
        previous_end = end
    return segments, cursor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bands", type=Path, required=True)
    parser.add_argument("--dos", type=Path, required=True)
    parser.add_argument("--pdos-dir", type=Path, required=True)
    parser.add_argument("--coords", type=Path, required=True)
    parser.add_argument("--seekpath", type=Path, required=True)
    parser.add_argument("--points-per-segment", type=int, required=True)
    parser.add_argument("--relax-start", type=Path, required=True)
    parser.add_argument("--relax-final", type=Path, required=True)
    parser.add_argument("--relax-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    path_data = json.loads(args.seekpath.read_text(encoding="utf-8"))
    path = path_data["path"]
    kcoords, eigenvalues, fermi_ha = read_eigenvalues(args.bands)
    segments, expected_kpoints = segment_indices(path, args.points_per_segment)
    if len(kcoords) != expected_kpoints:
        raise ValueError(f"Expected {expected_kpoints} k-points, found {len(kcoords)}")

    reciprocal = reciprocal_rows(args.coords)
    segment_x = []
    cursor_x = 0.0
    ticks = []
    for start, end, indices in segments:
        # A disconnected branch is not a calculated k-line. Give that jump
        # zero width and combine its endpoint labels (for example U|K).
        local = [cursor_x]
        for left, right in zip(indices[:-1], indices[1:]):
            delta = (kcoords[right] - kcoords[left]) @ reciprocal
            local.append(local[-1] + float(np.linalg.norm(delta)))
        local = np.asarray(local)
        segment_x.append((indices, local))
        ticks.extend([(float(local[0]), start), (float(local[-1]), end)])
        cursor_x = float(local[-1])

    tick_map = {}
    for position, label in ticks:
        tick_map.setdefault(round(position, 10), []).append(label)
    tick_positions = sorted(tick_map)
    tick_labels = []
    for position in tick_positions:
        labels = []
        for label in tick_map[position]:
            if label not in labels:
                labels.append(label)
        tick_labels.append("|".join(labels).replace("GAMMA", r"$\Gamma$"))

    energies_ev = eigenvalues * HARTREE_TO_EV - fermi_ha * HARTREE_TO_EV
    occupied_bands = 4
    valence = energies_ev[:, occupied_bands - 1]
    conduction = energies_ev[:, occupied_bands]
    indirect_gap = float(conduction.min() - valence.max())
    direct_gap = float(np.min(conduction - valence))

    dos = numeric_rows(args.dos)
    pdos_files = sorted(args.pdos_dir.glob("Atom*DOS_l.dat"))
    if len(pdos_files) != 2:
        raise ValueError(f"Expected two atom-pDOS files, found {len(pdos_files)}")
    projected = None
    for filename in pdos_files:
        values = numeric_rows(filename)
        projected = values if projected is None else projected + np.column_stack(
            (np.zeros(len(values)), values[:, 1:])
        )
    occupied_rows = dos[:, 0] <= 0.0
    integrated_electrons = float(dos[occupied_rows][-1, 2])
    relaxation_forces = force_history(args.relax_output)
    start_basis_error = diamond_basis_error(args.relax_start)
    final_basis_error = diamond_basis_error(args.relax_final)

    fig, (band_ax, dos_ax) = plt.subplots(
        1, 2, figsize=(13.5, 7.2), gridspec_kw={"width_ratios": [3.2, 1.25]},
        constrained_layout=True,
    )
    for indices, xvalues in segment_x:
        band_ax.plot(xvalues, energies_ev[indices], color="#155e75", linewidth=1.05)
    for position in tick_positions:
        band_ax.axvline(position, color="#9ca3af", linewidth=0.7)
    band_ax.axhline(0.0, color="#dc2626", linestyle="--", linewidth=1.0)
    band_ax.set_xticks(tick_positions, tick_labels)
    band_ax.set_xlim(tick_positions[0], tick_positions[-1])
    band_ax.set_ylim(-8, 6)
    band_ax.set_ylabel(r"Energy - $E_F$ (eV)")
    band_ax.set_title("Band structure")
    band_ax.grid(axis="y", color="#e5e7eb", linewidth=0.6)

    dos_ax.plot(dos[:, 1], dos[:, 0], color="#111827", label="total", linewidth=1.5)
    dos_ax.plot(projected[:, 2], projected[:, 0], color="#16a34a",
                linestyle="--", label="Si s", linewidth=1.2)
    dos_ax.plot(projected[:, 3], projected[:, 0], color="#d97706",
                label="Si p", linewidth=1.3)
    if projected.shape[1] > 4:
        dos_ax.plot(projected[:, 4], projected[:, 0], color="#7c3aed",
                    linestyle=":", label="Si d", linewidth=1.1)
    dos_ax.axhline(0.0, color="#dc2626", linestyle="--", linewidth=1.0)
    dos_ax.set_ylim(-8, 6)
    dos_ax.set_xlabel("DOS (states/eV)")
    dos_ax.set_yticklabels([])
    dos_ax.set_title("Density of states")
    dos_ax.legend(frameon=False, fontsize=9)
    dos_ax.grid(axis="y", color="#e5e7eb", linewidth=0.6)

    fig.suptitle("Primitive diamond Si - nonorthogonal FCC cell", fontsize=16)
    fig.text(
        0.5, 0.01,
        f"HPKOT/SeeK-path; path gap = {indirect_gap:.3f} eV; "
        f"minimum direct gap = {direct_gap:.3f} eV; DOS integral = "
        f"{integrated_electrons:.3f} e",
        ha="center", fontsize=9,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180)
    plt.close(fig)

    summary = {
        "spacegroup_number": path_data["spacegroup_number"],
        "spacegroup_international": path_data["spacegroup_international"],
        "bravais_lattice_extended": path_data["bravais_lattice_extended"],
        "path": path,
        "band_kpoints": len(kcoords),
        "indirect_path_gap_ev": indirect_gap,
        "minimum_direct_path_gap_ev": direct_gap,
        "integrated_electrons_at_fermi": integrated_electrons,
        "pdos_atom_files": len(pdos_files),
        "relax_initial_max_force_ha_per_bohr": relaxation_forces[0],
        "relax_final_max_force_ha_per_bohr": relaxation_forces[-1],
        "initial_basis_error_bohr": start_basis_error,
        "final_basis_error_bohr": final_basis_error,
    }
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
