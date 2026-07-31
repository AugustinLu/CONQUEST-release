#!/usr/bin/env python3
"""Validate the nonorthogonal blip calculation and MPI-rank invariance."""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path


def require(pattern: str, text: str, message: str) -> re.Match[str]:
    match = re.search(pattern, text, re.MULTILINE)
    if match is None:
        raise SystemExit(f"FAIL: {message}")
    return match


def parse_output(path: Path) -> dict[str, float]:
    if not path.is_file():
        raise SystemExit(f"FAIL: missing output file: {path}")
    text = path.read_text(errors="replace")
    require(
        r"Support functions represented with blip basis",
        text,
        f"{path}: CONQUEST did not select the blip basis",
    )
    require(
        r"Using blips as basis set for support functions",
        text,
        f"{path}: blip initialization was not reached",
    )
    require(
        r"Starting blip-coefficient variation",
        text,
        f"{path}: the inverse/derivative optimization path was not reached",
    )
    require(
        r"Support Variation #:\s+1",
        text,
        f"{path}: the requested support-function step was not performed",
    )
    require(
        r"PulayMixSC: Reached SCF tolerance",
        text,
        f"{path}: the calculation did not converge",
    )
    energy = float(
        require(
            r"Harris-Foulkes energy\s*=\s*([-+0-9.eEdD]+)\s+Ha",
            text,
            f"{path}: no final energy was printed",
        )
        .group(1)
        .replace("D", "E")
        .replace("d", "e")
    )
    electrons = float(
        require(
            r"Number of electrons\s*=\s*([-+0-9.eEdD]+)",
            text,
            f"{path}: no final electron count was printed",
        )
        .group(1)
        .replace("D", "E")
        .replace("d", "e")
    )
    runtime = float(
        require(
            r"Total run time was:\s*([-+0-9.eEdD]+)\s+seconds",
            text,
            f"{path}: calculation did not finish normally",
        )
        .group(1)
        .replace("D", "E")
        .replace("d", "e")
    )
    maximum_force = float(
        require(
            r"Maximum force\s*:\s*([-+0-9.eEdD]+)",
            text,
            f"{path}: force/second-derivative evaluation was not reached",
        )
        .group(1)
        .replace("D", "E")
        .replace("d", "e")
    )
    if not all(
        math.isfinite(value) for value in (energy, electrons, runtime, maximum_force)
    ):
        raise SystemExit(f"FAIL: {path}: a reported result is not finite")
    if re.search(r"\b(NaN|Infinity)\b", text, re.IGNORECASE):
        raise SystemExit(f"FAIL: {path}: non-finite value appears in the output")
    if abs(electrons - 32.0) > 1.0e-3:
        raise SystemExit(f"FAIL: {path}: unexpected electron count {electrons}")
    return {
        "energy_ha": energy,
        "electrons": electrons,
        "maximum_force_ha_per_bohr": maximum_force,
        "runtime_s": runtime,
    }


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "results")
    cases = {
        "np1": parse_output(root / "nonorthogonal_np1" / "Conquest_out"),
        "np2": parse_output(root / "nonorthogonal_np2" / "Conquest_out"),
    }
    reference_path = Path(__file__).parent / "reference" / "summary.json"
    reference = json.loads(reference_path.read_text())
    for name, result in cases.items():
        energy_error = abs(result["energy_ha"] - reference["energy_ha"])
        force_error = abs(
            result["maximum_force_ha_per_bohr"]
            - reference["maximum_force_ha_per_bohr"]
        )
        electron_error = abs(result["electrons"] - reference["electron_count"])
        if energy_error > reference["energy_tolerance_ha"]:
            raise SystemExit(
                f"FAIL: {name} energy differs from the maintained reference by "
                f"{energy_error:.3e} Ha"
            )
        if force_error > reference["force_tolerance_ha_per_bohr"]:
            raise SystemExit(
                f"FAIL: {name} maximum force differs from the maintained reference by "
                f"{force_error:.3e} Ha/bohr"
            )
        if electron_error > reference["electron_tolerance"]:
            raise SystemExit(
                f"FAIL: {name} electron count differs from the maintained reference by "
                f"{electron_error:.3e}"
            )

    rank_energy_error = abs(cases["np1"]["energy_ha"] - cases["np2"]["energy_ha"])
    rank_electron_error = abs(cases["np1"]["electrons"] - cases["np2"]["electrons"])
    if rank_energy_error > 1.0e-10:
        raise SystemExit(
            f"FAIL: one- and two-rank energies differ by {rank_energy_error:.3e} Ha"
        )
    if rank_electron_error > 1.0e-6:
        raise SystemExit(
            "FAIL: one- and two-rank electron counts differ by "
            f"{rank_electron_error:.3e}"
        )

    summary = {
        "status": "pass",
        "cell": "determinant-one 45-degree shear of conventional diamond Si",
        "support_variations": 1,
        "cases": cases,
        "rank_energy_error_ha": rank_energy_error,
        "rank_electron_error": rank_electron_error,
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        "PASS: nonorthogonal blip value/derivative/inverse regression; "
        f"energy={cases['np1']['energy_ha']:.12f} Ha; "
        f"rank error={rank_energy_error:.3e} Ha"
    )


if __name__ == "__main__":
    main()
