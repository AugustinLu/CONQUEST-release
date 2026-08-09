#!/usr/bin/env python3
"""Check that only a general lattice auto-enables Cartesian shear stress."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def stress_row_count(path: Path) -> int:
    lines = path.read_text().splitlines()
    for index, line in enumerate(lines):
        if "force: Total stress:" not in line:
            continue
        rows = 1
        for continuation in lines[index + 1:index + 3]:
            if re.match(r"^\s{20,}[-+0-9.]", continuation):
                rows += 1
        return rows
    raise ValueError(f"missing total stress in {path}")


root = Path(sys.argv[1])
axis_aligned = (root / "axis_aligned" / "Conquest_out").read_text()
general = (root / "general" / "Conquest_out").read_text()
warning = "General lattice requires the full stress tensor"

if warning in axis_aligned:
    raise ValueError("axis-aligned cell unexpectedly enabled full stress")
if warning not in general:
    raise ValueError("general cell did not report automatic full-stress activation")
if stress_row_count(root / "axis_aligned" / "Conquest_out") != 1:
    raise ValueError("axis-aligned default should retain diagonal-only stress output")
if stress_row_count(root / "general" / "Conquest_out") != 3:
    raise ValueError("general-cell default did not produce a full 3x3 stress tensor")

print("PASS: general cells automatically enable the full Cartesian stress tensor")
