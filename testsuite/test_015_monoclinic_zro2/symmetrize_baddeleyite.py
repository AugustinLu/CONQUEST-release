#!/usr/bin/env python3
"""Restore exact P21/c 4e orbits after unconstrained numerical relaxation."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def read_coords(filename: Path):
    lines = [
        line.strip()
        for line in filename.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    lattice = np.asarray(
        [[float(value) for value in lines[index].split()[:3]]
         for index in range(3)]
    )
    count = int(lines[3].split()[0])
    atoms = [lines[index].split() for index in range(4, 4 + count)]
    positions = np.asarray([[float(value) for value in atom[:3]] for atom in atoms])
    species = [atom[3] for atom in atoms]
    return lattice, positions, species


def wrapped_near(value, reference):
    return value + round(reference - value)


def asymmetric_position(orbit):
    reference = orbit[0]
    candidates = np.asarray(
        [
            orbit[0],
            -orbit[1],
            [-orbit[2, 0], orbit[2, 1] - 0.5, 0.5 - orbit[2, 2]],
            [orbit[3, 0], 0.5 - orbit[3, 1], orbit[3, 2] - 0.5],
        ]
    )
    for row in range(1, len(candidates)):
        candidates[row] = [
            wrapped_near(candidates[row, axis], reference[axis])
            for axis in range(3)
        ]
    return np.mean(candidates, axis=0)


def expand(position):
    x, y, z = position
    return np.asarray(
        [
            [x, y, z],
            [-x, -y, -z],
            [-x, y + 0.5, 0.5 - z],
            [x, 0.5 - y, 0.5 + z],
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    lattice, positions, species = read_coords(args.source)
    if len(positions) != 12:
        raise ValueError("Baddeleyite conventional cell must contain 12 atoms")
    symmetrized = np.vstack(
        [expand(asymmetric_position(positions[start:start + 4]))
         for start in (0, 4, 8)]
    )
    lines = [" ".join(f"{value:.14f}" for value in row) for row in lattice]
    lines.append(str(len(species)))
    for position, atom_species in zip(symmetrized, species, strict=True):
        lines.append(
            " ".join(f"{value:.14f}" for value in position)
            + f" {atom_species} T T T"
        )
    args.destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("P21/c 4e orbits restored for Zr, O1, and O2.")


if __name__ == "__main__":
    main()
