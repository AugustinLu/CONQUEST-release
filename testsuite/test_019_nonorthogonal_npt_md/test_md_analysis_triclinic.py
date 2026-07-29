#!/usr/bin/env python3
"""Check the Python exact minimum image for a skew cell."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--utilities", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.utilities.resolve()))
    from frame import Frame
    from md_tools import MSD, Pairdist, bohr2ang, diff_mic

    lattice = np.asarray(
        [[1.0, 0.0, 0.0], [0.8, 0.6, 0.0], [0.0, 0.0, 1.0]])
    fractional = np.asarray([0.49, 0.49, 0.10])
    displacement = fractional @ lattice
    exact = diff_mic(np.zeros(3), displacement, lattice)
    # np.ndindex is nonnegative; translate it to the [-5, 5]^3 box.
    candidates = [
        displacement - (np.asarray(index) - 5) @ lattice
        for index in np.ndindex(11, 11, 11)
    ]
    brute = min(candidates, key=lambda vector: np.dot(vector, vector))
    if not np.allclose(exact, brute, atol=2.0e-13, rtol=0.0):
        raise ValueError(f"triclinic MIC mismatch: {exact} versus {brute}")

    initial = Frame(2, 0)
    initial.lat = lattice.copy()
    initial.species[:] = [1, 1]
    positions = np.asarray([[0.1, 0.2, 0.3], [0.7, 0.8, 0.9]])
    initial.r = positions @ initial.lat
    deformed = Frame(2, 1)
    deformed.lat = np.asarray(
        [[1.05, 0.0, 0.0], [0.9, 0.57, 0.0], [0.0, 0.0, 1.02]])
    deformed.species[:] = initial.species
    deformed.r = positions @ deformed.lat
    rdf = Pairdist(2, 1, 2.0, 0.1, {1: "X"}, {1: 2})
    rdf.update_rdf(deformed)
    expected_volume = abs(np.linalg.det(deformed.lat))*bohr2ang**3
    if not np.isclose(rdf.volume, expected_volume):
        raise ValueError("triclinic RDF volume is not determinant-based")
    msd = MSD(2, 1.0, initial)
    msd.update_msd(1, deformed)
    if abs(msd.msd[-1]) > 1.0e-24:
        raise ValueError("pure affine cell deformation produced nonzero MSD")
    print("PASS: Python RDF/MSD utilities use exact triclinic MIC")


if __name__ == "__main__":
    main()
