#!/usr/bin/env python3
"""Check that atoms a hair below and a hair above a cell face give one result."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ENERGY_TOLERANCE = 1.0e-7  # Ha
FORCE_TOLERANCE = 1.0e-6  # Ha/a0
STRESS_TOLERANCE = 1.0e-4  # GPa
NUMBER = r"[-+]?\d+\.\d+(?:[eE][-+]?\d+)?"


def last_values(text: str, label: str, count: int) -> list[float]:
    words = r"\s*".join(re.escape(word) for word in label.split())
    pattern = words + r"\s*" + r"\s+".join([f"({NUMBER})"] * count)
    matches = re.findall(pattern, text)
    if not matches:
        raise ValueError(f"missing '{label}' in Conquest_out")
    last = matches[-1]
    return [float(value) for value in (last if isinstance(last, tuple) else (last,))]


def read_case(path: Path) -> dict[str, list[float]]:
    text = path.read_text()
    return {
        "energy": last_values(text, "DFT total energy =", 1),
        "max_force": last_values(text, "force: Maximum force :", 1),
        "force_residual": last_values(text, "force: Force Residual:", 1),
        "stress": last_values(text, "force: Total stress:", 3),
    }


root = Path(sys.argv[1])
below = read_case(root / "below_face" / "Conquest_out")
above = read_case(root / "above_face" / "Conquest_out")

tolerances = {
    "energy": ENERGY_TOLERANCE,
    "max_force": FORCE_TOLERANCE,
    "force_residual": FORCE_TOLERANCE,
    "stress": STRESS_TOLERANCE,
}
failures = []
for key, tolerance in tolerances.items():
    difference = max(abs(a - b) for a, b in zip(below[key], above[key]))
    print(f"{key}: below={below[key]} above={above[key]} "
          f"maximum absolute difference={difference:.3e} tolerance={tolerance:.1e}")
    if difference > tolerance:
        failures.append(key)

if above["max_force"][0] < 1.0e-4:
    raise ValueError("displaced atom gives no force; the force comparison is vacuous")
if failures:
    raise ValueError(
        "atoms within shift_in_bohr of a cell face are not handled consistently: "
        + ", ".join(failures)
    )

print("PASS: coordinates just below and just above a cell face are equivalent")
