#!/usr/bin/env bash
# Representative explicit-Ewald Hf force versus an energy finite difference.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
NP="${NP:-2}"
BACKGROUND_MODE="${BACKGROUND_MODE:-F}"
RUN_DIR="${RUN_DIR:-$SCRIPT_DIR/results/ewald_force_hf_x}"

if (( NP < 1 || NP > 4 )); then
  echo "ERROR: this 12-atom test permits one to four MPI ranks." >&2
  exit 2
fi
if [[ -e "$RUN_DIR" ]]; then
  archive="${RUN_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RUN_DIR" "$archive"
  echo "Previous force check preserved in $archive"
fi
mkdir -p "$RUN_DIR"
cp "$SCRIPT_DIR/HfCQ.ion" "$RUN_DIR/HfCQ.ion"
cp "$SCRIPT_DIR/OCQ.ion" "$RUN_DIR/OCQ.ion"
cp "$SCRIPT_DIR/coords_force_test.in" "$RUN_DIR/coords_force_test.in"
cp "$SCRIPT_DIR/ewald_force_hf_x.Conquest_input" "$RUN_DIR/Conquest_input"

(
  cd "$RUN_DIR"
  if [[ "$BACKGROUND_MODE" == T ]]; then
    /usr/sbin/taskpolicy -b "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" \
      > mpi.log 2>&1
  else
    "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" > mpi.log 2>&1
  fi
)

grep -q "Ewald total energy" "$RUN_DIR/Conquest_out"
grep -q "Numerical Force:" "$RUN_DIR/Conquest_out"
grep -E "Initial force|Final force|Numerical Force|Analytic Force|Force error" \
  "$RUN_DIR/Conquest_out"
force_error=$(awk '/Force error:/ {value=$3} END {print value}' \
  "$RUN_DIR/Conquest_out")
if ! awk -v error="$force_error" \
  'BEGIN {if (error < 0) error = -error; exit !(error <= 1.0e-4)}'; then
  echo "FAIL: force error ${force_error} Ha/a0 exceeds 1.0e-4 Ha/a0" >&2
  exit 1
fi
echo "PASS: |force error| = ${force_error#-} Ha/a0"
