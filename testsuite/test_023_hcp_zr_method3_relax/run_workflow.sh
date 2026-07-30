#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-python3}"
NP="${NP:-2}"
RESULTS_DIR="${RESULTS_DIR:-$SCRIPT_DIR/results}"

if (( NP < 1 || NP > 2 )); then
  echo "ERROR: the two-atom HCP example permits one or two MPI ranks." >&2
  exit 2
fi
if [[ ! -x "$CONQUEST_BIN" ]]; then
  echo "ERROR: executable not found: $CONQUEST_BIN" >&2
  exit 2
fi
if [[ -e "$RESULTS_DIR" ]]; then
  archive="${RESULTS_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RESULTS_DIR" "$archive"
  echo "Previous results preserved in $archive"
fi
mkdir -p "$RESULTS_DIR"
cp "$SCRIPT_DIR/Conquest_input" "$RESULTS_DIR/Conquest_input"
cp "$SCRIPT_DIR/coords.in" "$RESULTS_DIR/coords.in"
cp "$SCRIPT_DIR/../test_015_monoclinic_zro2/Zr.ion" "$RESULTS_DIR/Zr.ion"

(
  cd "$RESULTS_DIR"
  "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" > mpi.log 2>&1
)

[[ -s "$RESULTS_DIR/Conquest_out" ]]
[[ -s "$RESULTS_DIR/coord_next.dat" ]]
"$PYTHON" "$SCRIPT_DIR/check_cell.py" \
  "$SCRIPT_DIR/coords.in" "$RESULTS_DIR/coord_next.dat"
