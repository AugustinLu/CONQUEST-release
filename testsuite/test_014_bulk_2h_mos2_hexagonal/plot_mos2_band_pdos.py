#!/usr/bin/env python3
"""Plot bulk 2H-MoS2 bands and species/orbital-resolved pDOS."""

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


def force_history(filename: Path):
    return [
        float(value)
        for value in re.findall(
            r"Maximum force\s+:\s+([-+0-9.eE]+)",
            filename.read_text(encoding="utf-8"),
        )
    ]


def sulfur_z(filename: Path):
    lines = [
        line.strip()
        for line in filename.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    positions = np.asarray(
        [[float(value) for value in lines[index].split()[:3]] for index in range(4, 10)]
    )
    candidates = np.asarray(
        [
            positions[2, 2],
            positions[3, 2] + 0.5,
            1.0 - positions[4, 2],
            1.5 - positions[5, 2],
        ]
    )
    return float(np.mean(candidates))


def integrate_window(values, column, minimum, maximum):
    selected = (values[:, 0] >= minimum) & (values[:, 0] <= maximum)
    return float(np.trapezoid(values[selected, column], values[selected, 0]))


def main():
    parser = argparse.ArgumentParser()
    for name in (
        "bands",
        "dos",
        "pdos_dir",
        "seekpath",
        "relax_start",
        "relax_final",
        "relax_output",
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

    plotted = []
    ticks = []
    cursor_x = 0.0
    for start, end, indices in segments:
        # A disconnected HPKOT branch starts at the preceding x coordinate:
        # no white space is allocated to a line that was not calculated.
        xvalues = [cursor_x]
        for left, right in zip(indices[:-1], indices[1:]):
            xvalues.append(
                xvalues[-1] + np.linalg.norm(kcoords[right] - kcoords[left])
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
    occupied = 26
    valence = bands_ev[:, occupied - 1]
    conduction = bands_ev[:, occupied]
    indirect_gap = float(conduction.min() - valence.max())
    direct_gap = float(np.min(conduction - valence))
    vbm_index = int(np.argmax(valence))
    cbm_index = int(np.argmin(conduction))

    def locate(index):
        for start, end, indices in segments:
            offsets = np.flatnonzero(indices == index)
            if offsets.size:
                return {
                    "segment": [start, end],
                    "fraction_from_segment_start": float(
                        offsets[0] / (len(indices) - 1)
                    ),
                    "cartesian_k_bohr_inverse": kcoords[index].tolist(),
                }
        raise ValueError(f"Band-edge index {index} does not belong to the path")

    vbm_location = locate(vbm_index)
    cbm_location = locate(cbm_index)

    dos = numeric_rows(args.dos)
    files = sorted(args.pdos_dir.glob("Atom*DOS_l.dat"))
    if len(files) != 6:
        raise ValueError(f"Expected six atom pDOS files, found {len(files)}")
    atoms = [numeric_rows(filename) for filename in files]
    molybdenum = atoms[0].copy()
    molybdenum[:, 1:] += atoms[1][:, 1:]
    sulfur = atoms[2].copy()
    for values in atoms[3:]:
        sulfur[:, 1:] += values[:, 1:]

    occupied_rows = dos[:, 0] <= 0.0
    electron_integral = float(dos[occupied_rows][-1, 2])
    forces = force_history(args.relax_output)
    valence_s_p = integrate_window(sulfur, 3, -2.0, 0.0)
    valence_mo_d = integrate_window(molybdenum, 4, -2.0, 0.0)
    conduction_s_p = integrate_window(sulfur, 3, 0.0, 2.0)
    conduction_mo_d = integrate_window(molybdenum, 4, 0.0, 2.0)

    figure, (band_axis, dos_axis) = plt.subplots(
        1,
        2,
        figsize=(13.6, 7.2),
        gridspec_kw={"width_ratios": [3.25, 1.25]},
        constrained_layout=True,
    )
    for indices, xvalues in plotted:
        band_axis.plot(xvalues, bands_ev[indices], color="#0e7490", linewidth=0.9)
    for position in tick_positions:
        band_axis.axvline(position, color="#9ca3af", linewidth=0.7)
    band_axis.axhline(0.0, color="#dc2626", linestyle="--", linewidth=1.0)
    band_axis.set_xticks(tick_positions, tick_labels)
    band_axis.tick_params(axis="x", labelsize=9)
    band_axis.set_xlim(tick_positions[0], tick_positions[-1])
    band_axis.set_ylim(-8, 6)
    band_axis.set_ylabel(r"Energy - $E_F$ (eV)")
    band_axis.set_title("Band structure")
    band_axis.grid(axis="y", color="#e5e7eb", linewidth=0.6)

    dos_axis.plot(dos[:, 1], dos[:, 0], color="#111827", label="total", linewidth=1.5)
    dos_axis.plot(sulfur[:, 3], sulfur[:, 0], color="#d97706", label="S p", linewidth=1.4)
    dos_axis.plot(
        molybdenum[:, 4],
        molybdenum[:, 0],
        color="#7c3aed",
        label="Mo d",
        linewidth=1.4,
    )
    dos_axis.plot(
        sulfur[:, 2],
        sulfur[:, 0],
        color="#16a34a",
        linestyle="--",
        label="S s",
        linewidth=1.0,
    )
    dos_axis.axhline(0.0, color="#dc2626", linestyle="--", linewidth=1.0)
    dos_axis.set_ylim(-8, 6)
    dos_axis.set_xlabel("DOS (states/eV)")
    dos_axis.set_yticklabels([])
    dos_axis.set_title("Density of states")
    dos_axis.legend(frameon=False)
    dos_axis.grid(axis="y", color="#e5e7eb", linewidth=0.6)
    figure.suptitle(
        "Bulk 2H-MoS$_2$ - hexagonal P6$_3$/mmc (PBE, scalar relativistic)\n"
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
        "vbm": vbm_location,
        "cbm": cbm_location,
        "total_valence_electrons_from_scf": 52.0,
        "integrated_states_in_exported_dos_window_at_fermi": electron_integral,
        "relax_initial_max_force_ha_per_bohr": forces[0],
        "relax_final_max_force_ha_per_bohr": forces[-1],
        "sulfur_z_initial": sulfur_z(args.relax_start),
        "sulfur_z_final": sulfur_z(args.relax_final),
        "valence_minus2_to_0ev_s_p_weight": valence_s_p,
        "valence_minus2_to_0ev_mo_d_weight": valence_mo_d,
        "conduction_0_to_2ev_s_p_weight": conduction_s_p,
        "conduction_0_to_2ev_mo_d_weight": conduction_mo_d,
    }
    if path_data["spacegroup_number"] != 194:
        raise ValueError("Relaxed structure is not P6_3/mmc (space group 194)")
    if not 0.5 < indirect_gap < 1.5:
        raise ValueError(f"Unexpected scalar-PBE path gap: {indirect_gap:.6f} eV")
    if vbm_location["segment"][0] != "GAMMA" or vbm_location[
        "fraction_from_segment_start"
    ] != 0.0:
        raise ValueError(f"Expected the bulk VBM at Gamma, found {vbm_location}")
    if cbm_location["segment"] != ["K", "GAMMA"]:
        raise ValueError(f"Expected the CBM on K-Gamma, found {cbm_location}")
    if conduction_mo_d <= conduction_s_p:
        raise ValueError("Expected Mo d character to dominate the low conduction band")
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
