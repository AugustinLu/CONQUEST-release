#!/usr/bin/env python3
"""Check vdW-DFT invariance under a unimodular graphene-cell shear."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np


def last_value(pattern: str, text: str, label: str) -> float:
    values = re.findall(pattern, text, flags=re.IGNORECASE)
    if not values:
        raise RuntimeError(f"Could not find {label}")
    return float(values[-1].replace("D", "E").replace("d", "e"))


def read_case(root: Path, name: str) -> dict[str, float]:
    text = (root / name / "Conquest_out").read_text()
    return {
        "vdw_correction_ha": last_value(
            r"van der Waals correction to XC-energy\s*:\s*([-+0-9.eEdD]+)",
            text,
            "vdW correction",
        ),
        "corrected_energy_ha": last_value(
            r"Harris-Foulkes Energy after vdW correction\s*:\s*([-+0-9.eEdD]+)",
            text,
            "vdW-corrected Harris-Foulkes energy",
        ),
    }


def read_cell(path: Path) -> np.ndarray:
    lines = path.read_text().splitlines()
    # The file stores lattice vectors as rows; transpose to column convention.
    return np.array([[float(x) for x in line.split()] for line in lines[:3]]).T


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--energy-tolerance", type=float, default=2.0e-3)
    parser.add_argument("--correction-tolerance", type=float, default=2.0e-3)
    args = parser.parse_args()

    base_cell = read_cell(args.source / "coords_base.dat")
    sheared_cell = read_cell(args.source / "coords_sheared.dat")
    base = read_case(args.root, "base")
    sheared = read_case(args.root, "sheared")

    volumes = [abs(float(np.linalg.det(base_cell))),
               abs(float(np.linalg.det(sheared_cell)))]
    length_products = [
        float(np.prod(np.linalg.norm(base_cell, axis=0))),
        float(np.prod(np.linalg.norm(sheared_cell, axis=0))),
    ]
    result = {
        "base": base,
        "sheared": sheared,
        "cell_volume_bohr3": volumes,
        "vector_length_product_bohr3": length_products,
        "volume_difference_bohr3": abs(volumes[1] - volumes[0]),
        "length_product_ratio": length_products[1] / length_products[0],
        "corrected_energy_difference_ha": abs(
            sheared["corrected_energy_ha"] - base["corrected_energy_ha"]
        ),
        "vdw_correction_difference_ha": abs(
            sheared["vdw_correction_ha"] - base["vdw_correction_ha"]
        ),
        "energy_tolerance_ha": args.energy_tolerance,
        "correction_tolerance_ha": args.correction_tolerance,
    }

    if not all(math.isfinite(value) for case in (base, sheared)
               for value in case.values()):
        raise SystemExit("FAIL: non-finite vdW energy")
    if result["volume_difference_bohr3"] > 1.0e-8:
        raise SystemExit("FAIL: input cells do not have the same determinant")
    # The literature cell is rounded to eight decimal places, so the ratio is
    # sqrt(3) only to about 3e-5.
    if abs(result["length_product_ratio"] - math.sqrt(3.0)) > 1.0e-4:
        raise SystemExit("FAIL: shear does not provide the intended length-product test")
    if result["corrected_energy_difference_ha"] > args.energy_tolerance:
        raise SystemExit(
            "FAIL: corrected total-energy representation residual "
            f"{result['corrected_energy_difference_ha']:.6e} Ha"
        )
    if result["vdw_correction_difference_ha"] > args.correction_tolerance:
        raise SystemExit(
            "FAIL: vdW correction representation residual "
            f"{result['vdw_correction_difference_ha']:.6e} Ha"
        )

    args.summary.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
