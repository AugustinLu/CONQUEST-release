#!/usr/bin/env python3
"""Plot rutile TiO2 bands and species/orbital-resolved pDOS."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HA_TO_EV = 27.211386245988


def numeric_rows(filename):
    rows = []
    for line in filename.read_text(encoding="utf-8").splitlines():
        try:
            if line.strip() and not line.lstrip().startswith(("#", "&")):
                rows.append([float(value) for value in line.split()])
        except ValueError:
            pass
    return np.asarray(rows)


def read_eigenvalues(filename):
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


def segments(path, count):
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


def force_history(filename):
    return [float(value) for value in re.findall(
        r"Maximum force\s+:\s+([-+0-9.eE]+)",
        filename.read_text(encoding="utf-8"),
    )]


def oxygen_u(filename):
    lines = [line.strip() for line in filename.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    count = int(lines[3].split()[0])
    positions = np.asarray([
        [float(value) for value in lines[index].split()[:3]]
        for index in range(4, 4 + count)
    ])
    candidates = np.mod([
        positions[2, 0], positions[2, 1],
        1.0 - positions[3, 0], 1.0 - positions[3, 1],
        positions[4, 0] - 0.5, 0.5 - positions[4, 1],
        0.5 - positions[5, 0], positions[5, 1] - 0.5,
    ], 1.0)
    return float(np.mean(candidates))


def main():
    parser = argparse.ArgumentParser()
    for name in ("bands", "dos", "pdos_dir", "coords", "seekpath",
                 "relax_start", "relax_final", "relax_output", "output", "summary"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    parser.add_argument("--points-per-segment", type=int, required=True)
    args = parser.parse_args()

    path_data = json.loads(args.seekpath.read_text(encoding="utf-8"))
    path = path_data["path"]
    kcoords, eigenvalues, fermi = read_eigenvalues(args.bands)
    path_segments, expected = segments(path, args.points_per_segment)
    if len(kcoords) != expected:
        raise ValueError(f"Expected {expected} k-points, found {len(kcoords)}")
    reciprocal = np.linalg.inv(np.loadtxt(args.coords, max_rows=3)).T
    plotted_segments = []
    ticks = []
    cursor_x = 0.0
    for start, end, indices in path_segments:
        # Do not allocate x-axis distance to an uncalculated branch jump.
        # Coincident endpoint ticks are merged below as "end|start".
        xvalues = [cursor_x]
        for left, right in zip(indices[:-1], indices[1:]):
            xvalues.append(xvalues[-1] + np.linalg.norm(
                (kcoords[right] - kcoords[left]) @ reciprocal
            ))
        xvalues = np.asarray(xvalues)
        plotted_segments.append((indices, xvalues))
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
    occupied = 24
    valence = bands_ev[:, occupied - 1]
    conduction = bands_ev[:, occupied]
    indirect_gap = float(conduction.min() - valence.max())
    direct_gap = float(np.min(conduction - valence))

    dos = numeric_rows(args.dos)
    files = sorted(args.pdos_dir.glob("Atom*DOS_l.dat"))
    if len(files) != 6:
        raise ValueError(f"Expected six atom pDOS files, found {len(files)}")
    atom_pdos = [numeric_rows(filename) for filename in files]
    ti = atom_pdos[0].copy()
    ti[:, 1:] += atom_pdos[1][:, 1:]
    oxygen = atom_pdos[2].copy()
    for values in atom_pdos[3:]:
        oxygen[:, 1:] += values[:, 1:]
    occupied_rows = dos[:, 0] <= 0.0
    electron_integral = float(dos[occupied_rows][-1, 2])
    forces = force_history(args.relax_output)

    fig, (band_ax, dos_ax) = plt.subplots(
        1, 2, figsize=(13.5, 7.2), gridspec_kw={"width_ratios": [3.2, 1.25]},
        constrained_layout=True,
    )
    for indices, xvalues in plotted_segments:
        band_ax.plot(xvalues, bands_ev[indices], color="#155e75", linewidth=0.9)
    for position in tick_positions:
        band_ax.axvline(position, color="#9ca3af", linewidth=0.7)
    band_ax.axhline(0.0, color="#dc2626", linestyle="--", linewidth=1.0)
    band_ax.set_xticks(tick_positions, tick_labels)
    band_ax.set_xlim(tick_positions[0], tick_positions[-1])
    band_ax.set_ylim(-10, 8)
    band_ax.set_ylabel(r"Energy - $E_F$ (eV)")
    band_ax.set_title("Band structure")
    band_ax.grid(axis="y", color="#e5e7eb", linewidth=0.6)

    dos_ax.plot(dos[:, 1], dos[:, 0], color="#111827", label="total", linewidth=1.5)
    dos_ax.plot(oxygen[:, 3], oxygen[:, 0], color="#d97706",
                label="O p", linewidth=1.4)
    dos_ax.plot(ti[:, 4], ti[:, 0], color="#7c3aed",
                label="Ti d", linewidth=1.4)
    dos_ax.plot(oxygen[:, 2], oxygen[:, 0], color="#16a34a",
                linestyle="--", label="O s", linewidth=1.0)
    dos_ax.axhline(0.0, color="#dc2626", linestyle="--", linewidth=1.0)
    dos_ax.set_ylim(-10, 8)
    dos_ax.set_xlabel("DOS (states/eV)")
    dos_ax.set_yticklabels([])
    dos_ax.set_title("Density of states")
    dos_ax.legend(frameon=False)
    dos_ax.grid(axis="y", color="#e5e7eb", linewidth=0.6)
    fig.suptitle(
        "Rutile TiO$_2$ - tetragonal P4$_2$/mnm (LDA)\n"
        f"HPKOT/SeeK-path direct gap = {direct_gap:.3f} eV",
        fontsize=15,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180)
    plt.close(fig)

    summary = {
        "spacegroup_number": path_data["spacegroup_number"],
        "spacegroup_international": path_data["spacegroup_international"],
        "path": path,
        "band_kpoints": len(kcoords),
        "indirect_path_gap_ev": indirect_gap,
        "minimum_direct_path_gap_ev": direct_gap,
        "total_valence_electrons_from_scf": 48.0,
        "integrated_states_in_exported_dos_window_at_fermi": electron_integral,
        "dos_window_note": "16 deep Ti semicore electrons lie below the exported window",
        "relax_initial_max_force_ha_per_bohr": forces[0],
        "relax_final_max_force_ha_per_bohr": forces[-1],
        "oxygen_u_initial": oxygen_u(args.relax_start),
        "oxygen_u_final": oxygen_u(args.relax_final),
    }
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
