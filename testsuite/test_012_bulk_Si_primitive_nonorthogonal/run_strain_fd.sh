#!/usr/bin/env bash
# Six analytic-stress versus central-energy-derivative checks.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
NP="${NP:-2}"
BACKGROUND_MODE="${BACKGROUND_MODE:-auto}"
RUN_DIR="${RUN_DIR:-$SCRIPT_DIR/results/strain_finite_difference}"

if [[ "$BACKGROUND_MODE" == auto ]]; then
  if [[ "$(uname -s)" == Darwin && -x /usr/sbin/taskpolicy ]]; then
    BACKGROUND_MODE=T
  else
    BACKGROUND_MODE=F
  fi
fi
if (( NP < 1 || NP > 2 )); then
  echo "ERROR: primitive Si has two atoms; NP must be 1 or 2." >&2
  exit 2
fi
if [[ -e "$RUN_DIR" ]]; then
  archive="${RUN_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RUN_DIR" "$archive"
  echo "Previous strain check preserved in $archive"
fi
mkdir -p "$RUN_DIR/.matplotlib"
"$PYTHON" "$SCRIPT_DIR/strain_finite_difference.py" prepare \
  --base "$SCRIPT_DIR/coords_ideal.dat" --root "$RUN_DIR" \
  > "$RUN_DIR/prepare.log"

for directory in "$RUN_DIR"/base "$RUN_DIR"/*_minus "$RUN_DIR"/*_plus; do
  cp "$SCRIPT_DIR/Si.ion" "$directory/Si.ion"
  cp "$SCRIPT_DIR/strain_static.Conquest_input" "$directory/Conquest_input"
  echo "Running $(basename "$directory")"
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
done

MPLCONFIGDIR="$RUN_DIR/.matplotlib" "$PYTHON" \
  "$SCRIPT_DIR/strain_finite_difference.py" analyse \
  --root "$RUN_DIR" \
  --summary "$RUN_DIR/summary.json" \
  --image "$RUN_DIR/primitive_si_six_strain_validation.png"
