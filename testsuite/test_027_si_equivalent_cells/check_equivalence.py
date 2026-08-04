#!/usr/bin/env python3
"""Check primitive/conventional diamond-Si energy and stress equivalence."""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

HA_TO_EV = 27.211386245988


def require(pattern: str, text: str, message: str) -> re.Match[str]:
    match = re.search(pattern, text, re.MULTILINE)
    if match is None:
        raise SystemExit(f"FAIL: {message}")
    return match


def number(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))


def sampled_gap(path: Path, occupied_band: int) -> float:
    if not path.is_file():
        raise SystemExit(f"FAIL: missing eigenvalue file: {path}")
    valence_max = -math.inf
    conduction_min = math.inf
    for line in path.read_text(errors="replace").splitlines():
        fields = line.split()
        if len(fields) != 2 or not fields[0].isdigit():
            continue
        band = int(fields[0])
        eigenvalue = number(fields[1])
        if band == occupied_band:
            valence_max = max(valence_max, eigenvalue)
        elif band == occupied_band + 1:
            conduction_min = min(conduction_min, eigenvalue)
    if not math.isfinite(valence_max) or not math.isfinite(conduction_min):
        raise SystemExit(f"FAIL: could not determine sampled gap from {path}")
    return (conduction_min - valence_max) * HA_TO_EV


def parse_case(path: Path, expected_electrons: float, occupied_band: int) -> dict:
    output = path / "Conquest_out"
    if not output.is_file():
        raise SystemExit(f"FAIL: missing output file: {output}")
    text = output.read_text(errors="replace")
    require(
        r"The functional used will be GGA PBE96",
        text,
        f"{output}: calculation did not use PBE",
    )
    require(
        r"PulayMixSC: Reached SCF tolerance",
        text,
        f"{output}: SCF did not converge",
    )
    energy = number(
        require(
            r"DFT total energy\s*=\s*([-+0-9.eEdD]+)\s+Ha",
            text,
            f"{output}: final DFT energy was not printed",
        ).group(1)
    )
    electrons = number(
        require(
            r"Number of electrons\s*=\s*([-+0-9.eEdD]+)",
            text,
            f"{output}: electron count was not printed",
        ).group(1)
    )
    stress_match = require(
        r"Total stress:\s*([-+0-9.eEdD]+)\s+([-+0-9.eEdD]+)\s+([-+0-9.eEdD]+)\s+GPa",
        text,
        f"{output}: diagonal stress was not printed",
    )
    stress = [number(stress_match.group(i)) for i in range(1, 4)]
    if not all(math.isfinite(value) for value in [energy, electrons, *stress]):
        raise SystemExit(f"FAIL: {output}: a parsed result is non-finite")
    if abs(electrons - expected_electrons) > 1.0e-3:
        raise SystemExit(
            f"FAIL: {output}: electron count {electrons} differs from "
            f"{expected_electrons}"
        )
    return {
        "energy_ha": energy,
        "electrons": electrons,
        "diagonal_stress_gpa": stress,
        "sampled_gap_ev": sampled_gap(path / "eigenvalues.dat", occupied_band),
    }


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "results")
    cubic = parse_case(root / "cubic", expected_electrons=32.0, occupied_band=16)
    primitive = parse_case(root / "primitive", expected_electrons=8.0, occupied_band=4)

    cubic_per_primitive = cubic["energy_ha"] / 4.0
    energy_error = abs(primitive["energy_ha"] - cubic_per_primitive)
    stress_error = max(
        abs(left - right)
        for left, right in zip(
            primitive["diagonal_stress_gpa"], cubic["diagonal_stress_gpa"]
        )
    )

    # Dense meshes are matched in reciprocal-basis resolution to the nearest
    # integer, rather than being exactly the same integration quadrature.
    if energy_error > 2.0e-5:
        raise SystemExit(
            "FAIL: primitive and cubic energy/2-atom-cell differ by "
            f"{energy_error:.3e} Ha"
        )
    # The cutoff selects separate FFT-friendly integer grids for the two cell
    # shapes (96^3 cubic and 72^3 primitive at 400 Ha), so their stress
    # quadratures are not algebraically commensurate even at the same nominal
    # cutoff.  The tolerance remains below 1% of the hydrostatic stress.
    if stress_error > 5.0e-2:
        raise SystemExit(
            f"FAIL: primitive and cubic diagonal stresses differ by {stress_error:.3e} GPa"
        )
    if primitive["sampled_gap_ev"] < 0.2:
        raise SystemExit(
            "FAIL: primitive diamond Si is not insulating on the sampled mesh; "
            f"gap={primitive['sampled_gap_ev']:.6f} eV"
        )

    summary = {
        "status": "pass",
        "grid_cutoff_ha": 400,
        "k_meshes": {"primitive": [19, 19, 19], "cubic": [11, 11, 11]},
        "cases": {"cubic": cubic, "primitive": primitive},
        "cubic_energy_per_primitive_ha": cubic_per_primitive,
        "energy_error_ha_per_primitive": energy_error,
        "energy_error_mev_per_atom": energy_error * HA_TO_EV * 500.0,
        "maximum_diagonal_stress_error_gpa": stress_error,
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        "PASS: equivalent diamond-Si cells; "
        f"energy error={energy_error:.3e} Ha/2 atoms "
        f"({summary['energy_error_mev_per_atom']:.4f} meV/atom); "
        f"stress error={stress_error:.3e} GPa"
    )


if __name__ == "__main__":
    main()
