#!/usr/bin/env python3
"""Summarise the primitive-Si full-lattice relaxation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np


BOHR_TO_ANGSTROM = 0.529177210903


def read_frame(filename: Path):
    lines = [line.strip() for line in filename.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    offset = 0
    lattice = None
    fractional = None
    while offset < len(lines):
        lattice = np.asarray([
            [float(value) for value in lines[offset + index].split()[:3]]
            for index in range(3)
        ])
        atom_count = int(lines[offset + 3].split()[0])
        fractional = np.asarray([
            [float(value) for value in lines[offset + index].split()[:3]]
            for index in range(4, 4 + atom_count)
        ])
        offset += 4 + atom_count
    if lattice is None or fractional is None:
        raise ValueError(f"No coordinate frame found in {filename}")
    return lattice, fractional


def lattice_metrics(lattice):
    lengths = np.linalg.norm(lattice, axis=1)
    angles = []
    for first, second in ((1, 2), (0, 2), (0, 1)):
        cosine = np.dot(lattice[first], lattice[second]) / (
            lengths[first] * lengths[second]
        )
        angles.append(float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))))
    volume = abs(float(np.linalg.det(lattice)))
    return {
        "lattice_bohr": lattice.tolist(),
        "vector_lengths_bohr": lengths.tolist(),
        "angles_degrees_alpha_beta_gamma": angles,
        "volume_bohr3": volume,
        "equivalent_conventional_a_angstrom": (
            (4.0 * volume) ** (1.0 / 3.0) * BOHR_TO_ANGSTROM
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial", type=Path, required=True)
    parser.add_argument("--final", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    initial_lattice, initial_fractional = read_frame(args.initial)
    final_lattice, final_fractional = read_frame(args.final)
    text = args.output.read_text(encoding="utf-8")
    iterations = [
        {
            "iteration": int(match.group(1)),
            "maximum_stress_gpa": float(match.group(2)),
            "enthalpy_ha": float(match.group(3)),
            "enthalpy_change_ha": float(match.group(4)),
        }
        for match in re.finditer(
            r"GeomOpt\s+- Iter:\s+(\d+)\s+MaxStr:\s+([-+0-9.eE]+)"
            r"\s+GPa H:\s+([-+0-9.eE]+)\s+Ha\s+dH:\s+([-+0-9.eE]+)Ha",
            text,
        )
    ]
    summary = {
        "converged": "GeomOpt converged" in text,
        "initial": lattice_metrics(initial_lattice),
        "final": lattice_metrics(final_lattice),
        "maximum_fractional_coordinate_change": float(
            np.max(np.abs(final_fractional - initial_fractional))
        ),
        "geometry_iterations": iterations,
    }
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
