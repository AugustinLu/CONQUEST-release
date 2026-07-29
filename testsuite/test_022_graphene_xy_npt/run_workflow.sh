#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
NP="${NP:-4}"
RESULTS_DIR="${RESULTS_DIR:-$SCRIPT_DIR/results}"

if (( NP < 1 || NP > 4 )); then
  echo "ERROR: NP must be between 1 and 4." >&2
  exit 2
fi
if [[ -e "$RESULTS_DIR" ]]; then
  archive="${RESULTS_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RESULTS_DIR" "$archive"
fi
mkdir -p "$RESULTS_DIR"
cp "$SCRIPT_DIR/Conquest_input" "$SCRIPT_DIR/coords.dat" "$RESULTS_DIR/"
cp "$SCRIPT_DIR/../test_010_graphite_monoclinic/band_graphene_workflow/C.ion" \
  "$RESULTS_DIR/C.ion"

(
  cd "$RESULTS_DIR"
  "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" > mpi.log 2>&1
)
grep -q "MD step:      2" "$RESULTS_DIR/Conquest_out"
"$PYTHON" "$SCRIPT_DIR/analyse_xy_npt.py"
