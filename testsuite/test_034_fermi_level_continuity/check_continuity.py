#!/usr/bin/env python3
"""Reject discontinuous energy or Fermi-level changes across tiny strains."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


root = Path(sys.argv[1])
records = []
for microstrain in (184, 185, 186, 187):
    output = root / f"d{microstrain}" / "Conquest_out"
    text = output.read_text(encoding="utf-8")
    energies = re.findall(r"Harris-Foulkes energy\s+=\s+([-+0-9.eE]+)", text)
    fermi = re.findall(r"Fermi energy for spin\s*=\s*1 is\s+([-+0-9.eE]+)", text)
    if not energies or not fermi or "Reached SCF tolerance" not in text:
        raise ValueError(f"incomplete calculation in {output.parent}")
    records.append({
        "yy_microstrain": microstrain,
        "energy_ha": float(energies[-1]),
        "fermi_energy_ha": float(fermi[-1]),
    })

energy_increments = [
    records[index + 1]["energy_ha"] - records[index]["energy_ha"]
    for index in range(3)
]
fermi_increments = [
    records[index + 1]["fermi_energy_ha"] - records[index]["fermi_energy_ha"]
    for index in range(3)
]
energy_nonlinearity = max(energy_increments) - min(energy_increments)
maximum_fermi_step = max(abs(value) for value in fermi_increments)

summary = {
    "records": records,
    "successive_energy_increments_ha": energy_increments,
    "energy_increment_range_ha": energy_nonlinearity,
    "successive_fermi_increments_ha": fermi_increments,
    "maximum_fermi_step_ha": maximum_fermi_step,
}
(root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

if energy_nonlinearity >= 1.0e-9:
    raise ValueError(
        "neighboring strain-energy increments are discontinuous: "
        f"range {energy_nonlinearity:.6e} Ha"
    )
if maximum_fermi_step >= 1.0e-4:
    raise ValueError(
        f"Fermi level jumped by {maximum_fermi_step:.6e} Ha inside the gap"
    )

print(
    "PASS: Fermi level and energy are continuous across neighboring strains; "
    f"energy-increment range {energy_nonlinearity:.3e} Ha, "
    f"maximum Fermi step {maximum_fermi_step:.3e} Ha"
)
