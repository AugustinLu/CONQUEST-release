#!/usr/bin/env python3
"""Check that a CONQUEST run actually exercised the blip basis and completed."""

from __future__ import annotations

import math
import json
import re
import sys
from pathlib import Path


def require(pattern: str, text: str, message: str) -> re.Match[str]:
    match = re.search(pattern, text, re.MULTILINE)
    if match is None:
        raise SystemExit(f"FAIL: {message}")
    return match


def main() -> None:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "Conquest_out")
    if not output.is_file():
        raise SystemExit(f"FAIL: missing output file: {output}")

    text = output.read_text(errors="replace")
    require(
        r"Support functions represented with blip basis",
        text,
        "CONQUEST did not report the blip basis",
    )
    require(
        r"Using blips as basis set for support functions",
        text,
        "blip coefficient initialization was not reached",
    )
    require(
        r"PulayMixSC: Reached SCF tolerance",
        text,
        "the blip calculation did not converge",
    )
    energy_match = require(
        r"Harris-Foulkes energy\s*=\s*([-+0-9.eEdD]+)\s+Ha",
        text,
        "no final Harris-Foulkes energy was printed",
    )
    electron_match = require(
        r"Number of electrons\s*=\s*([-+0-9.eEdD]+)",
        text,
        "no final electron count was printed",
    )
    runtime_match = require(
        r"Total run time was:\s*([-+0-9.eEdD]+)\s+seconds",
        text,
        "the calculation did not reach normal completion",
    )

    energy = float(energy_match.group(1).replace("D", "E").replace("d", "e"))
    electrons = float(
        electron_match.group(1).replace("D", "E").replace("d", "e")
    )
    runtime = float(runtime_match.group(1).replace("D", "E").replace("d", "e"))
    if not math.isfinite(energy):
        raise SystemExit("FAIL: final energy is not finite")
    if not math.isfinite(runtime) or runtime < 0.0:
        raise SystemExit("FAIL: reported runtime is invalid")
    if re.search(r"\b(NaN|Infinity)\b", text, re.IGNORECASE):
        raise SystemExit("FAIL: non-finite value appears in CONQUEST output")

    reference_path = Path(__file__).parent / "reference" / "summary.json"
    reference = json.loads(reference_path.read_text())
    energy_error = abs(energy - reference["harris_foulkes_energy_ha"])
    electron_error = abs(electrons - reference["electron_count"])
    if energy_error > reference["energy_tolerance_ha"]:
        raise SystemExit(
            "FAIL: Harris-Foulkes energy differs from the blip reference by "
            f"{energy_error:.3e} Ha"
        )
    if electron_error > reference["electron_tolerance"]:
        raise SystemExit(
            f"FAIL: electron count differs from the reference by {electron_error:.3e}"
        )

    print(
        "PASS: orthorhombic blip smoke test; "
        f"energy={energy:.12f} Ha; electrons={electrons:.6f}"
    )


if __name__ == "__main__":
    main()
