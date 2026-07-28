#!/usr/bin/env bash
# Six explicit-Ewald analytic-stress versus central-energy-derivative checks.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
NP="${NP:-2}"
BACKGROUND_MODE="${BACKGROUND_MODE:-F}"
RUN_DIR="${RUN_DIR:-$SCRIPT_DIR/results/ewald_strain_finite_difference}"

if (( NP < 1 || NP > 4 )); then
  echo "ERROR: this 12-atom test permits one to four MPI ranks." >&2
  exit 2
fi
if [[ -e "$RUN_DIR" ]]; then
  archive="${RUN_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RUN_DIR" "$archive"
  echo "Previous strain check preserved in $archive"
fi
mkdir -p "$RUN_DIR/.matplotlib"
"$PYTHON" "$SCRIPT_DIR/ewald_strain_finite_difference.py" prepare \
  --base "$SCRIPT_DIR/coords.dat" --root "$RUN_DIR" \
  > "$RUN_DIR/prepare.log"

for directory in "$RUN_DIR"/base "$RUN_DIR"/*_minus "$RUN_DIR"/*_plus; do
  cp "$SCRIPT_DIR/HfCQ.ion" "$directory/HfCQ.ion"
  cp "$SCRIPT_DIR/OCQ.ion" "$directory/OCQ.ion"
  cp "$SCRIPT_DIR/ewald_strain_static.Conquest_input" \
    "$directory/Conquest_input"
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
  grep -q "Ewald total energy" "$directory/Conquest_out"
done

MPLCONFIGDIR="$RUN_DIR/.matplotlib" "$PYTHON" \
  "$SCRIPT_DIR/ewald_strain_finite_difference.py" analyse \
  --root "$RUN_DIR" \
  --summary "$RUN_DIR/summary.json" \
  --image "$RUN_DIR/monoclinic_hfo2_ewald_six_strain_validation.png" \
  --ewald-tolerance-gpa 0.01 \
  --total-tolerance-gpa 0.10
