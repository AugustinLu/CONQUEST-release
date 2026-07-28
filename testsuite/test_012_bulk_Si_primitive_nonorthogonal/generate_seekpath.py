#!/usr/bin/env python3
"""Generate a SeeK-path band path in the input cell's reciprocal basis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import seekpath


BOHR_TO_ANGSTROM = 0.529177210903


def read_conquest_coords(filename: Path):
    lines = [
        line.split("#", 1)[0].strip()
        for line in filename.read_text(encoding="utf-8").splitlines()
    ]
    lines = [line for line in lines if line]
    lattice = [[float(value) * BOHR_TO_ANGSTROM for value in lines[i].split()[:3]]
               for i in range(3)]
    atom_count = int(lines[3].split()[0])
    positions = []
    numbers = []
    for line in lines[4:4 + atom_count]:
        fields = line.split()
        positions.append([float(value) for value in fields[:3]])
        numbers.append(int(fields[3]))
    return lattice, positions, numbers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("coords", type=Path)
    parser.add_argument("--output", type=Path, default=Path("seekpath.json"))
    parser.add_argument("--symprec", type=float, default=1.0e-5)
    args = parser.parse_args()

    result = seekpath.get_path_orig_cell(
        read_conquest_coords(args.coords),
        recipe="hpkot",
        with_time_reversal=True,
        symprec=args.symprec,
    )
    serializable = {
        "source": str(args.coords),
        "recipe": "HPKOT",
        "spacegroup_number": result["spacegroup_number"],
        "spacegroup_international": result["spacegroup_international"],
        "bravais_lattice_extended": result["bravais_lattice_extended"],
        "path": [list(segment) for segment in result["path"]],
        "point_coords": {
            label: [float(value) for value in coordinates]
            for label, coordinates in result["point_coords"].items()
        },
    }
    args.output.write_text(json.dumps(serializable, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(serializable, indent=2))


if __name__ == "__main__":
    main()
