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
mkdir -p "$RESULTS_DIR/volume" "$RESULTS_DIR/xyz"
for constraint in volume xyz; do
  directory="$RESULTS_DIR/$constraint"
  cp "$SCRIPT_DIR/../test_012_bulk_Si_primitive_nonorthogonal/Si.ion" \
    "$directory/Si.ion"
  cp "$SCRIPT_DIR/coords.dat" "$directory/coords.dat"
  if [[ "$constraint" == volume ]]; then
    cp "$SCRIPT_DIR/Conquest_input" "$directory/Conquest_input"
  else
    cp "$SCRIPT_DIR/Conquest_input_xyz" "$directory/Conquest_input"
  fi

  (
    cd "$directory"
    if [[ "$BACKGROUND_MODE" == T ]]; then
      /usr/sbin/taskpolicy -b "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" \
        > mpi.log 2>&1
    else
      "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" > mpi.log 2>&1
    fi
  )
  grep -q "MD step:      1" "$directory/Conquest_out"
  [[ -s "$directory/md.frames" ]]
  [[ -s "$directory/trajectory.xyz" ]]
done

method3_directory="$RESULTS_DIR/method3_smoke"
mkdir -p "$method3_directory"
cp "$SCRIPT_DIR/../test_012_bulk_Si_primitive_nonorthogonal/Si.ion" \
  "$method3_directory/Si.ion"
cp "$SCRIPT_DIR/coords.dat" "$method3_directory/coords.dat"
cp "$SCRIPT_DIR/Conquest_input_method3_smoke" \
  "$method3_directory/Conquest_input"
(
  cd "$method3_directory"
  if [[ "$BACKGROUND_MODE" == T ]]; then
    /usr/sbin/taskpolicy -b "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" \
      > mpi.log 2>&1
  else
    "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" > mpi.log 2>&1
  fi
)
grep -q "starting relaxation with safemin line minimisation" \
  "$method3_directory/Conquest_out"
[[ -s "$method3_directory/coord_next.dat" ]]

"$PYTHON" "$SCRIPT_DIR/analyse_npt_cell.py" \
  --root "$RESULTS_DIR" --source "$SCRIPT_DIR" \
  --summary "$RESULTS_DIR/summary.json"

MPLCONFIGDIR="$RESULTS_DIR/.matplotlib" "$PYTHON" \
  "$SCRIPT_DIR/test_md_analysis_triclinic.py" \
  --utilities "$RELEASE_DIR/src/utilities"
