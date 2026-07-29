#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
NP="${NP:-4}"
RESULTS_DIR="${RESULTS_DIR:-$SCRIPT_DIR/results}"
RESTART_DIR="${RESTART_DIR:-$SCRIPT_DIR/results_restart}"

if (( NP < 1 || NP > 4 )); then
  echo "ERROR: NP must be between 1 and 4." >&2
  exit 2
fi
if [[ -e "$RESULTS_DIR" ]]; then
  archive="${RESULTS_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RESULTS_DIR" "$archive"
fi
if [[ -e "$RESTART_DIR" ]]; then
  archive="${RESTART_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RESTART_DIR" "$archive"
fi
mkdir -p "$RESULTS_DIR"
cp "$SCRIPT_DIR/Conquest_input" "$SCRIPT_DIR/coords.dat" "$RESULTS_DIR/"
cp "$SCRIPT_DIR/../test_011_hfo2/HfCQ.ion" "$RESULTS_DIR/HfCQ.ion"
cp "$SCRIPT_DIR/../test_011_hfo2/OCQ.ion" "$RESULTS_DIR/OCQ.ion"

(
  cd "$RESULTS_DIR"
  "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" > mpi.log 2>&1
)
grep -q "MD step:      2" "$RESULTS_DIR/Conquest_out"

mkdir -p "$RESTART_DIR"
cp "$SCRIPT_DIR/Conquest_input" "$SCRIPT_DIR/coords.dat" "$RESTART_DIR/"
cp "$SCRIPT_DIR/../test_011_hfo2/HfCQ.ion" "$RESTART_DIR/HfCQ.ion"
cp "$SCRIPT_DIR/../test_011_hfo2/OCQ.ion" "$RESTART_DIR/OCQ.ion"
(
  cd "$RESTART_DIR"
  "$PYTHON" -c \
    'from pathlib import Path; p=Path("Conquest_input"); t=p.read_text(); p.write_text(t.replace("AtomMove.NumSteps           2", "AtomMove.NumSteps           1"))'
  "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" > first_half_mpi.log 2>&1
  "$PYTHON" -c \
    'from pathlib import Path; p=Path("Conquest_input"); t=p.read_text(); p.write_text(t.replace("AtomMove.TypeOfRun          md", "AtomMove.TypeOfRun          md\nAtomMove.RestartRun         T"))'
  "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" > restart_mpi.log 2>&1
)
grep -q "MD step:      2" "$RESTART_DIR/Conquest_out"
"$PYTHON" "$SCRIPT_DIR/analyse_full_npt.py"
