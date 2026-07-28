#!/usr/bin/env python3
"""Project a relaxed rutile frame back onto its P42/mnm internal coordinate."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def last_frame(filename: Path):
    lines = [line.strip() for line in filename.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    offset = 0
    frame = None
    while offset < len(lines):
        lattice = np.asarray([
            [float(value) for value in lines[offset + index].split()[:3]]
            for index in range(3)
        ])
        count = int(lines[offset + 3].split()[0])
        positions = np.asarray([
            [float(value) for value in lines[offset + index].split()[:3]]
            for index in range(4, 4 + count)
        ])
        frame = lattice, positions
        offset += 4 + count
    if frame is None:
        raise ValueError(f"No frame in {filename}")
    return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    lattice, positions = last_frame(args.input)
    u_values = np.asarray([
        positions[2, 0], positions[2, 1],
        1.0 - positions[3, 0], 1.0 - positions[3, 1],
        positions[4, 0] - 0.5, 0.5 - positions[4, 1],
        0.5 - positions[5, 0], positions[5, 1] - 0.5,
    ])
    u = float(np.mean(np.mod(u_values, 1.0)))
    symmetric = [
        (0.0, 0.0, 0.0, 1, "F F F"),
        (0.5, 0.5, 0.5, 1, "F F F"),
        (u, u, 0.0, 2, "T T F"),
        (1.0 - u, 1.0 - u, 0.0, 2, "T T F"),
        (0.5 + u, 0.5 - u, 0.5, 2, "T T F"),
        (0.5 - u, 0.5 + u, 0.5, 2, "T T F"),
    ]
    output = [" ".join(f"{value:.14f}" for value in row) for row in lattice]
    output.append("6")
    output.extend(
        f"{x % 1.0:.14f} {y % 1.0:.14f} {z % 1.0:.14f} {species} {flags}"
        for x, y, z, species, flags in symmetric
    )
    args.output.write_text("\n".join(output) + "\n", encoding="utf-8")
    print(f"rutile oxygen u = {u:.12f}")


if __name__ == "__main__":
    main()
