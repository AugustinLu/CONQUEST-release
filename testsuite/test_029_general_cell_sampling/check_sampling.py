#!/usr/bin/env python3
"""Validate FFT-cutoff containment and automatic k-point spacing."""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np


root = Path(sys.argv[1])
text = (root / "Conquest_out").read_text()
lattice = np.loadtxt(root / "coords.dat", max_rows=3)
grid_cutoff = 20.0
requested_dk = 3.0

grid_match = re.search(
    r"Integration grid size:\s*(\d+)\s*x\s*(\d+)\s*x\s*(\d+)", text
)
mesh_match = re.search(
    r"Monkhorst-Pack mesh:\s*(\d+)\s*x\s*(\d+)\s*x\s*(\d+)", text
)
if not grid_match or not mesh_match:
    raise ValueError("missing integration-grid or Monkhorst-Pack dimensions")

grid = np.asarray([int(value) for value in grid_match.groups()])
mesh = np.asarray([int(value) for value in mesh_match.groups()])
direct_norms = np.linalg.norm(lattice, axis=1)
reciprocal = 2.0 * math.pi * np.linalg.inv(lattice).T
reciprocal_norms = np.linalg.norm(reciprocal, axis=1)

# The distance from the origin to FFT index face i is pi*N_i/|a_i|.
# Every face must lie beyond the requested |G| = sqrt(2*cutoff) sphere.
nyquist_face_distances = math.pi * grid / direct_norms
required_g = math.sqrt(2.0 * grid_cutoff)
if np.any(nyquist_face_distances <= required_g):
    raise ValueError(
        f"FFT box does not contain cutoff sphere: {nyquist_face_distances}"
    )

k_spacings = reciprocal_norms / mesh
if np.any(k_spacings > requested_dk * (1.0 + 1.0e-12)):
    raise ValueError(f"automatic k-point spacing exceeds Diag.dk: {k_spacings}")
if tuple(mesh) != (3, 1, 1):
    raise ValueError(f"unexpected extreme-skew k-mesh {tuple(mesh)}")

print(
    "PASS: FFT cutoff sphere is contained and automatic k-point spacing "
    "uses reciprocal-vector norms"
)
