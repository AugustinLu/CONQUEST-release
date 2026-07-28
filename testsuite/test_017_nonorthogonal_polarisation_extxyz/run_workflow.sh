#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
NP="${NP:-2}"
BACKGROUND_MODE="${BACKGROUND_MODE:-F}"
RESULTS_DIR="${RESULTS_DIR:-$SCRIPT_DIR/results}"

if (( NP < 1 || NP > 2 )); then
  echo "ERROR: primitive Si has two atoms; NP must be 1 or 2." >&2
  exit 2
fi
if [[ -e "$RESULTS_DIR" ]]; then
  archive="${RESULTS_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RESULTS_DIR" "$archive"
fi
mkdir -p "$RESULTS_DIR/base" "$RESULTS_DIR/sheared"

for representation in base sheared; do
  directory="$RESULTS_DIR/$representation"
  cp "$SCRIPT_DIR/../test_012_bulk_Si_primitive_nonorthogonal/Si.ion" \
    "$directory/Si.ion"
  cp "$SCRIPT_DIR/coords_${representation}.dat" "$directory/coords.dat"
  cp "$SCRIPT_DIR/Conquest_input" "$directory/Conquest_input"
  (
    cd "$directory"
    if [[ "$BACKGROUND_MODE" == T ]]; then
      /usr/sbin/taskpolicy -b "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" \
        > mpi.log 2>&1
    else
      "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" > mpi.log 2>&1
    fi
  )
  grep -q "Reached SCF tolerance" "$directory/Conquest_out"
  grep -q "Quantum of polarisation" "$directory/Conquest_out"
  [[ -s "$directory/trajectory.xyz" ]]
done

"$PYTHON" "$SCRIPT_DIR/analyse_polarisation_extxyz.py" \
  --root "$RESULTS_DIR" --summary "$RESULTS_DIR/summary.json"
