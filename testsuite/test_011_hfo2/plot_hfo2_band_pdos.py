#!/usr/bin/env python3
"""Plot monoclinic HfO2 bands and species/orbital-resolved pDOS."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HA_TO_EV = 27.211386245988


def numeric_rows(filename: Path):
    rows = []
    for line in filename.read_text(encoding="utf-8").splitlines():
        try:
            if line.strip() and not line.lstrip().startswith(("#", "&")):
                rows.append([float(value) for value in line.split()])
        except ValueError:
            pass
    return np.asarray(rows)


def read_eigenvalues(filename: Path):
    lines = filename.read_text(encoding="utf-8").splitlines()
    header = re.search(r"#\s+(\d+)\s+eigenvalues\s+(\d+)\s+kpoints", lines[0])
    fermi = re.search(r"Ef:\s+([-+0-9.eE]+)", lines[1])
    if not header or not fermi:
        raise ValueError(f"Cannot parse {filename}")
    bands, kpoints = map(int, header.groups())
    kcoords = np.empty((kpoints, 3))
    values = np.empty((kpoints, bands))
    cursor = 3
    for ikpt in range(kpoints):
        while not lines[cursor].strip():
            cursor += 1
        fields = lines[cursor].split()
        cursor += 1
        kcoords[ikpt] = [float(value) for value in fields[1:4]]
        for iband in range(bands):
            values[ikpt, iband] = float(lines[cursor].split()[1])
            cursor += 1
    return kcoords, values, float(fermi.group(1))


def path_segments(path, count):
    result = []
    cursor = 0
    previous = None
    for start, end in path:
        if start == previous:
            indices = np.arange(cursor - 1, cursor + count - 1)
            cursor += count - 1
        else:
            indices = np.arange(cursor, cursor + count)
            cursor += count
        result.append((start, end, indices))
        previous = end
    return result, cursor


def integrate_window(values, column, minimum, maximum):
    selected = (values[:, 0] >= minimum) & (values[:, 0] <= maximum)
    return float(np.trapezoid(values[selected, column], values[selected, 0]))


def atom_number(filename: Path):
    match = re.search(r"Atom(\d+)", filename.name)
    if not match:
        raise ValueError(f"Cannot identify atom number in {filename}")
    return int(match.group(1))


def main():
    parser = argparse.ArgumentParser()
    for name in (
        "bands",
        "dos",
        "pdos_dir",
        "coords",
        "seekpath",
        "output",
        "summary",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    parser.add_argument("--points-per-segment", type=int, required=True)
    args = parser.parse_args()

    path_data = json.loads(args.seekpath.read_text(encoding="utf-8"))
    path = path_data["path"]
    kcoords, eigenvalues, fermi = read_eigenvalues(args.bands)
    segments, expected = path_segments(path, args.points_per_segment)
    if len(kcoords) != expected:
        raise ValueError(f"Expected {expected} k-points, found {len(kcoords)}")

    lattice = np.loadtxt(args.coords, max_rows=3)
    reciprocal = np.linalg.inv(lattice).T
    plotted = []
    ticks = []
    cursor_x = 0.0
    for start, end, indices in segments:
        xvalues = [cursor_x]
        for left, right in zip(indices[:-1], indices[1:]):
            xvalues.append(
                xvalues[-1]
                + np.linalg.norm((kcoords[right] - kcoords[left]) @ reciprocal)
            )
        xvalues = np.asarray(xvalues)
        plotted.append((indices, xvalues))
        ticks.extend(((float(xvalues[0]), start), (float(xvalues[-1]), end)))
        cursor_x = float(xvalues[-1])
    tick_map = {}
    for position, label in ticks:
        tick_map.setdefault(round(position, 10), []).append(label)
    tick_positions = sorted(tick_map)
    tick_labels = [
        "|".join(dict.fromkeys(tick_map[position])).replace("GAMMA", r"$\Gamma$")
        for position in tick_positions
    ]

    bands_ev = (eigenvalues - fermi) * HA_TO_EV
    occupied = 48
    valence = bands_ev[:, occupied - 1]
    conduction = bands_ev[:, occupied]
    indirect_gap = float(conduction.min() - valence.max())
    direct_gap = float(np.min(conduction - valence))

    dos = numeric_rows(args.dos)
    files = sorted(args.pdos_dir.glob("Atom*DOS_l.dat"), key=atom_number)
    if len(files) != 12:
        raise ValueError(f"Expected 12 atom pDOS files, found {len(files)}")
    atoms = [numeric_rows(filename) for filename in files]
    hafnium = atoms[0].copy()
    for values in atoms[1:4]:
        hafnium[:, 1:] += values[:, 1:]
    oxygen = atoms[4].copy()
    for values in atoms[5:]:
        oxygen[:, 1:] += values[:, 1:]
    valence_o_p = integrate_window(oxygen, 3, -5.0, 0.0)
    valence_hf_d = integrate_window(hafnium, 4, -5.0, 0.0)
    conduction_o_p = integrate_window(oxygen, 3, 0.0, 5.0)
    conduction_hf_d = integrate_window(hafnium, 4, 0.0, 5.0)

    figure, (band_axis, dos_axis) = plt.subplots(
        1,
        2,
        figsize=(14.2, 7.4),
        gridspec_kw={"width_ratios": [3.35, 1.25]},
        constrained_layout=True,
    )
    for indices, xvalues in plotted:
        band_axis.plot(xvalues, bands_ev[indices], color="#155e75", linewidth=0.85)
    for position in tick_positions:
        band_axis.axvline(position, color="#9ca3af", linewidth=0.65)
    band_axis.axhline(0.0, color="#dc2626", linestyle="--", linewidth=1.0)
    band_axis.set_xticks(tick_positions, tick_labels)
    band_axis.tick_params(axis="x", labelsize=8)
    band_axis.set_xlim(tick_positions[0], tick_positions[-1])
    band_axis.set_ylim(-9, 8)
    band_axis.set_ylabel(r"Energy - $E_F$ (eV)")
    band_axis.set_title("Band structure")
    band_axis.grid(axis="y", color="#e5e7eb", linewidth=0.6)

    dos_axis.plot(dos[:, 1], dos[:, 0], color="#111827", label="total", linewidth=1.5)
    dos_axis.plot(oxygen[:, 3], oxygen[:, 0], color="#d97706",
                  label="O p", linewidth=1.4)
    dos_axis.plot(hafnium[:, 4], hafnium[:, 0], color="#7c3aed",
                  label="Hf d", linewidth=1.4)
    dos_axis.plot(oxygen[:, 2], oxygen[:, 0], color="#16a34a",
                  linestyle="--", label="O s", linewidth=1.0)
    dos_axis.axhline(0.0, color="#dc2626", linestyle="--", linewidth=1.0)
    dos_axis.set_ylim(-9, 8)
    dos_axis.set_xlabel("DOS (states/eV)")
    dos_axis.set_yticklabels([])
    dos_axis.set_title("Density of states")
    dos_axis.legend(frameon=False)
    dos_axis.grid(axis="y", color="#e5e7eb", linewidth=0.6)
    figure.suptitle(
        "Monoclinic HfO$_2$ - P2$_1$/c (PBE/DZP, scalar relativistic)\n"
        f"HPKOT path gap = {indirect_gap:.3f} eV; "
        f"minimum direct gap = {direct_gap:.3f} eV",
        fontsize=15,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180)
    plt.close(figure)

    summary = {
        "spacegroup_number": path_data["spacegroup_number"],
        "spacegroup_international": path_data["spacegroup_international"],
        "bravais_lattice_extended": path_data["bravais_lattice_extended"],
        "path": path,
        "band_kpoints": len(kcoords),
        "indirect_path_gap_ev": indirect_gap,
        "minimum_direct_path_gap_ev": direct_gap,
        "total_valence_electrons_from_scf": 96.0,
        "valence_minus5_to_0ev_o_p_weight": valence_o_p,
        "valence_minus5_to_0ev_hf_d_weight": valence_hf_d,
        "conduction_0_to_5ev_o_p_weight": conduction_o_p,
        "conduction_0_to_5ev_hf_d_weight": conduction_hf_d,
        "basis": "DZP",
        "spin_orbit": False,
    }
    if path_data["spacegroup_number"] != 14:
        raise ValueError("Relaxed structure is not P2_1/c (space group 14)")
    if not 2.0 < indirect_gap < 6.0:
        raise ValueError(f"Unexpected PBE path gap: {indirect_gap:.6f} eV")
    if valence_o_p <= valence_hf_d:
        raise ValueError("Expected O p character to dominate the upper valence band")
    if conduction_hf_d <= conduction_o_p:
        raise ValueError("Expected Hf d character to dominate the low conduction band")
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
