#!/usr/bin/env python3
import argparse
from pathlib import Path

import numpy as np

BOHR_TO_ANG = 0.529177210903
EXPECTED_FRACTIONAL = np.array(((0.17, 0.29, 0.41), (0.73, 0.11, 0.62)))


def read_native_lattice(path: Path) -> np.ndarray:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for _ in range(3):
            rows.append([float(value) for value in handle.readline().split()])
    return np.array(rows, dtype=float).T * BOHR_TO_ANG


def read_pdb(path: Path):
    scale = np.zeros((3, 3), dtype=float)
    origin = np.zeros(3, dtype=float)
    found = np.zeros(3, dtype=bool)
    coordinates = []
    cryst_lengths = None
    for line in path.read_text(encoding="utf-8").splitlines():
        record = line[:6]
        if record == "CRYST1":
            cryst_lengths = np.array(
                (float(line[6:15]), float(line[15:24]), float(line[24:33]))
            )
        elif record in ("SCALE1", "SCALE2", "SCALE3"):
            row = int(record[-1]) - 1
            scale[row] = [
                float(line[10:20]),
                float(line[20:30]),
                float(line[30:40]),
            ]
            origin[row] = float(line[45:55])
            found[row] = True
        elif record in ("ATOM  ", "HETATM"):
            coordinates.append(
                [float(line[30:38]), float(line[38:46]), float(line[46:54])]
            )
    if not np.all(found):
        raise AssertionError(f"{path} does not contain all three SCALE records")
    if cryst_lengths is None:
        raise AssertionError(f"{path} does not contain CRYST1")
    lattice = np.linalg.inv(scale)
    fractional = np.array(coordinates) @ scale.T + origin
    return lattice, fractional, cryst_lengths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--coords", type=Path, required=True)
    parser.add_argument("--native-pdb", type=Path, required=True)
    parser.add_argument("--restart-pdb", type=Path, required=True)
    args = parser.parse_args()

    expected_lattice = read_native_lattice(args.coords)
    native_lattice, native_fractional, cryst_lengths = read_pdb(args.native_pdb)
    restart_lattice, restart_fractional, restart_lengths = read_pdb(args.restart_pdb)

    lattice_error = float(np.max(np.abs(native_lattice - expected_lattice)))
    restart_lattice_error = float(np.max(np.abs(restart_lattice - native_lattice)))
    fractional_error = float(np.max(np.abs(native_fractional - EXPECTED_FRACTIONAL)))
    restart_fractional_error = float(
        np.max(np.abs(restart_fractional - native_fractional))
    )
    metric_error = float(
        np.max(np.abs(cryst_lengths - np.linalg.norm(native_lattice, axis=0)))
    )
    restart_metric_error = float(np.max(np.abs(restart_lengths - cryst_lengths)))

    if lattice_error > 1.0e-4:
        raise AssertionError(f"native PDB lattice orientation error: {lattice_error}")
    if restart_lattice_error > 1.0e-4:
        raise AssertionError(f"restart PDB lattice error: {restart_lattice_error}")
    if fractional_error > 3.0e-4:
        raise AssertionError(f"native PDB fractional-coordinate error: {fractional_error}")
    if restart_fractional_error > 3.0e-4:
        raise AssertionError(
            f"restart PDB fractional-coordinate error: {restart_fractional_error}"
        )
    if metric_error > 1.0e-3 or restart_metric_error > 1.0e-3:
        raise AssertionError(
            f"CRYST1/SCALE metric mismatch: {metric_error}, {restart_metric_error}"
        )

    print("PASS: rotated triclinic PDB lattice and fractional coordinates round-trip")
    print(f"maximum lattice error (Angstrom): {lattice_error:.3e}")
    print(f"maximum fractional-coordinate error: {fractional_error:.3e}")


if __name__ == "__main__":
    main()
