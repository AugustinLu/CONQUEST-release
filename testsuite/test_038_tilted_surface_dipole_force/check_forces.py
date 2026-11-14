#!/usr/bin/env python3
"""Compare analytic z forces with central differences of the energy."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

STEP = 0.01
TOLERANCE = 1.0e-4  # Ha/a0
root = Path(sys.argv[1])


def read(case):
    text = (root / case / "Conquest_out").read_text(encoding="utf-8")
    if "Reached SCF tolerance" not in text:
        raise ValueError(f"SCF did not converge in {case}")
    energy = float(re.findall(r"Harris-Foulkes energy\s+=\s+([-+0-9.eE]+)", text)[-1])
    forces = re.findall(r"force:\s+\d+\s+(\S+)\s+(\S+)\s+(\S+)", text)[-3:]
    return energy, [[float(x) for x in row] for row in forces]


_, forces = read("c0")
records = []
for atom, label in ((1, "O"), (2, "H")):
    e_plus, _ = read(f"a{atom}p")
    e_minus, _ = read(f"a{atom}m")
    fd = -(e_plus - e_minus) / (2.0 * STEP)
    analytic = forces[atom - 1][2]
    records.append({"atom": atom, "species": label, "analytic_fz": analytic,
                    "finite_difference_fz": fd, "difference": fd - analytic})

summary = {"step_bohr": STEP, "tolerance_ha_per_bohr": TOLERANCE,
           "records": records,
           "pass": all(abs(r["difference"]) < TOLERANCE for r in records)}
(root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
for r in records:
    print("%s  analytic %.8f  FD %.8f  diff %+.2e" %
          (r["species"], r["analytic_fz"], r["finite_difference_fz"], r["difference"]))
print("PASS" if summary["pass"] else "FAIL")
sys.exit(0 if summary["pass"] else 1)
