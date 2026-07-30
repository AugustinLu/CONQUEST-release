#!/usr/bin/env python3
"""Plot and validate published 3R-graphite bands and carbon-resolved pDOS."""

from __future__ import annotations

import argparse
import json
import math
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
    values = np.asarray(rows)
    if values.ndim != 2 or not np.all(np.isfinite(values)):
        raise ValueError(f"Cannot parse finite numeric rows from {filename}")
    return values


def read_eigenvalues(filename: Path):
    lines = filename.read_text(encoding="utf-8").splitlines()
    header = re.search(r"#\s+(\d+)\s+eigenvalues\s+(\d+)\s+kpoints", lines[0])
    fermi = re.search(r"Ef:\s+([-+0-9.eE]+)", lines[1])
    if not header or not fermi:
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
    if not np.all(np.isfinite(kcoords)) or not np.all(np.isfinite(eigenvalues)):
        raise ValueError("Band output contains non-finite values")
    return kcoords, eigenvalues, float(fermi.group(1))


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


def pretty_label(label: str) -> str:
    if label == "GAMMA":
        return r"$\Gamma$"
    if "_" not in label:
        return label
    base, subscript = label.split("_", 1)
    return rf"${base}_{{{subscript}}}$"


def integrate_window(values: np.ndarray, column: int, lower: float, upper: float):
    selected = (values[:, 0] >= lower) & (values[:, 0] <= upper)
    if np.count_nonzero(selected) < 2:
        raise ValueError("pDOS integration window is empty")
    return float(np.trapezoid(values[selected, column], values[selected, 0]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bands", type=Path, required=True)
    parser.add_argument("--dos", type=Path, required=True)
    parser.add_argument("--pdos-dir", type=Path, required=True)
    parser.add_argument("--coords", type=Path, required=True)
    parser.add_argument("--seekpath", type=Path, required=True)
    parser.add_argument("--points-per-segment", type=int, required=True)
    parser.add_argument("--gaussian-width-ha", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    path_data = json.loads(args.seekpath.read_text(encoding="utf-8"))
    path = path_data["path"]
    if path_data["spacegroup_number"] != 166:
        raise ValueError("The band path is not for R-3m (space group 166)")

    kcoords, eigenvalues, fermi_ha = read_eigenvalues(args.bands)
    segments, expected_kpoints = segment_indices(path, args.points_per_segment)
    if len(kcoords) != expected_kpoints:
        raise ValueError(
            f"Expected {expected_kpoints} band k-points, found {len(kcoords)}"
        )
    if eigenvalues.shape[1] < 5:
        raise ValueError("Too few bands to bracket the four occupied bands")

    lattice = np.loadtxt(args.coords, max_rows=3)
    reciprocal = np.linalg.inv(lattice).T
    plotted = []
    ticks = []
    cursor_x = 0.0
    for start, end, indices in segments:
        xvalues = [cursor_x]
        for left, right in zip(indices[:-1], indices[1:]):
            delta = (kcoords[right] - kcoords[left]) @ reciprocal
            xvalues.append(xvalues[-1] + float(np.linalg.norm(delta)))
        xvalues = np.asarray(xvalues)
        plotted.append((indices, xvalues))
        ticks.extend(((float(xvalues[0]), start), (float(xvalues[-1]), end)))
        cursor_x = float(xvalues[-1])

    tick_map = {}
    for position, label in ticks:
        tick_map.setdefault(round(position, 10), []).append(label)
    tick_positions = sorted(tick_map)
    tick_labels = [
        "|".join(
            pretty_label(label)
            for label in dict.fromkeys(tick_map[position])
        )
        for position in tick_positions
    ]

    bands_ev = (eigenvalues - fermi_ha) * HARTREE_TO_EV
    occupied = 4
    valence = bands_ev[:, occupied - 1]
    conduction = bands_ev[:, occupied]
    indirect_path_gap = float(conduction.min() - valence.max())
    minimum_direct_separation = float(np.min(conduction - valence))

    dos = numeric_rows(args.dos)
    pdos_files = sorted(args.pdos_dir.glob("Atom*DOS_l.dat"))
    if len(pdos_files) != 2:
        raise ValueError(f"Expected two atom-pDOS files, found {len(pdos_files)}")
    atom_pdos = [numeric_rows(filename) for filename in pdos_files]
    carbon = atom_pdos[0].copy()
    carbon[:, 1:] += atom_pdos[1][:, 1:]
    occupied_rows = dos[:, 0] <= 0.0
    if not np.any(occupied_rows):
        raise ValueError("DOS does not cover the Fermi level")
    integrated_electrons = float(dos[occupied_rows][-1, 2])
    near_fermi_s = integrate_window(carbon, 2, -2.0, 2.0)
    near_fermi_p = integrate_window(carbon, 3, -2.0, 2.0)

    if not 7.8 < integrated_electrons < 8.2:
        raise ValueError(
            f"Unexpected DOS electron integral: {integrated_electrons:.6f}"
        )
    if near_fermi_p <= near_fermi_s:
        raise ValueError("Carbon p character does not dominate near the Fermi level")
    if not -0.5 < indirect_path_gap < 0.5:
        raise ValueError(
            f"Unexpected graphite path gap: {indirect_path_gap:.6f} eV"
        )
    metrics = [
        indirect_path_gap,
        minimum_direct_separation,
        integrated_electrons,
        near_fermi_s,
        near_fermi_p,
    ]
    if not all(math.isfinite(value) for value in metrics):
        raise ValueError("Electronic-structure summary contains non-finite values")

    figure, (band_axis, dos_axis) = plt.subplots(
        1,
        2,
        figsize=(13.6, 7.2),
        gridspec_kw={"width_ratios": [3.25, 1.25]},
        constrained_layout=True,
    )
    for indices, xvalues in plotted:
        band_axis.plot(xvalues, bands_ev[indices], color="#155e75", linewidth=0.95)
    for position in tick_positions:
        band_axis.axvline(position, color="#9ca3af", linewidth=0.7)
    band_axis.axhline(0.0, color="#dc2626", linestyle="--", linewidth=1.0)
    band_axis.set_xticks(tick_positions, tick_labels)
    band_axis.set_xlim(tick_positions[0], tick_positions[-1])
    band_axis.set_ylim(-10.0, 8.0)
    band_axis.set_ylabel(r"Energy - $E_F$ (eV)")
    band_axis.set_title("Band structure")
    band_axis.grid(axis="y", color="#e5e7eb", linewidth=0.6)

    dos_axis.plot(dos[:, 1], dos[:, 0], color="#111827", label="total",
                  linewidth=1.5)
    dos_axis.plot(carbon[:, 2], carbon[:, 0], color="#16a34a",
                  linestyle="--", label="C s", linewidth=1.2)
    dos_axis.plot(carbon[:, 3], carbon[:, 0], color="#d97706", label="C p",
                  linewidth=1.4)
    dos_axis.axhline(0.0, color="#dc2626", linestyle="--", linewidth=1.0)
    dos_axis.set_ylim(-10.0, 8.0)
    dos_axis.set_xlabel("DOS (states/eV)")
    dos_axis.set_yticklabels([])
    dos_axis.set_title("Density of states")
    dos_axis.legend(frameon=False)
    dos_axis.grid(axis="y", color="#e5e7eb", linewidth=0.6)
    figure.suptitle(
        "Published 3R graphite - primitive rhombohedral R-3m\n"
        f"HPKOT path; Gaussian pDOS width = "
        f"{args.gaussian_width_ha:.3f} Ha",
        fontsize=15,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180)
    plt.close(figure)

    summary = {
        "status": "pass",
        "spacegroup_number": path_data["spacegroup_number"],
        "spacegroup_international": path_data["spacegroup_international"],
        "bravais_lattice_extended": path_data["bravais_lattice_extended"],
        "path": path,
        "band_kpoints": len(kcoords),
        "bands": int(eigenvalues.shape[1]),
        "occupied_bands": occupied,
        "gaussian_width_ha": args.gaussian_width_ha,
        "gaussian_width_ev": args.gaussian_width_ha * HARTREE_TO_EV,
        "indirect_path_gap_ev": indirect_path_gap,
        "minimum_direct_path_separation_ev": minimum_direct_separation,
        "integrated_electrons_at_fermi": integrated_electrons,
        "pdos_atom_files": len(pdos_files),
        "carbon_s_weight_minus2_to_2ev": near_fermi_s,
        "carbon_p_weight_minus2_to_2ev": near_fermi_p,
    }
    args.summary.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
