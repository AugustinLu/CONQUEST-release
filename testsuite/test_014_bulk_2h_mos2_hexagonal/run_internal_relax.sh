#!/usr/bin/env bash
# Symmetry-preserving relaxation of the sulfur internal coordinate.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
NP="${NP:-2}"
BACKGROUND_MODE="${BACKGROUND_MODE:-F}"
RUN_DIR="${RUN_DIR:-$SCRIPT_DIR/results/internal_relax}"

if (( NP < 1 || NP > 4 )); then
  echo "ERROR: this six-atom test permits one to four MPI ranks." >&2
  exit 2
fi
if [[ ! -x "$CONQUEST_BIN" ]]; then
  echo "ERROR: CONQUEST executable not found: $CONQUEST_BIN" >&2
  exit 2
fi
if [[ -e "$RUN_DIR" ]]; then
  archive="${RUN_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RUN_DIR" "$archive"
  echo "Previous internal relaxation preserved in $archive"
fi
mkdir -p "$RUN_DIR"
cp "$SCRIPT_DIR/coords_relax_start.dat" "$RUN_DIR/coords.dat"
cp "$SCRIPT_DIR/Mo.ion" "$RUN_DIR/Mo.ion"
cp "$SCRIPT_DIR/S.ion" "$RUN_DIR/S.ion"
cp "$SCRIPT_DIR/internal_relax.Conquest_input" "$RUN_DIR/Conquest_input"

(
  cd "$RUN_DIR"
  if [[ "$BACKGROUND_MODE" == T ]]; then
    /usr/sbin/taskpolicy -b "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" \
      > mpi.log 2>&1
  else
    "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" > mpi.log 2>&1
  fi
)

grep -q "GeomOpt converged" "$RUN_DIR/Conquest_out"
grep -q "Reached SCF tolerance" "$RUN_DIR/Conquest_out"
grep -Eq "Number of electrons[[:space:]]*=[[:space:]]*52\\.0" \
  "$RUN_DIR/Conquest_out"
if grep -Eq "ERROR|CQ_ABORT|NaN" "$RUN_DIR/Conquest_out"; then
  echo "FAIL: error marker found in CONQUEST output" >&2
  exit 1
fi

initial_force=$(grep "GeomOpt - Iter:" "$RUN_DIR/Conquest_out" |
  head -1 | sed -E 's/.*MaxF:[[:space:]]*([-+0-9.eE]+).*/\1/')
final_force=$(grep "GeomOpt - Iter:" "$RUN_DIR/Conquest_out" |
  tail -1 | sed -E 's/.*MaxF:[[:space:]]*([-+0-9.eE]+).*/\1/')
echo "PASS: sulfur internal relaxation converged; MaxF ${initial_force} -> ${final_force} Ha/a0."
