#!/usr/bin/env bash
# Run an extreme-skew spatial-decomposition check on one and two MPI ranks.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
BACKGROUND_MODE="${BACKGROUND_MODE:-F}"
RESULTS_DIR="${RESULTS_DIR:-$SCRIPT_DIR/results}"
SI_TEST="$RELEASE_DIR/testsuite/test_012_bulk_Si_primitive_nonorthogonal"

for executable in "$CONQUEST_BIN" "$PYTHON"; do
  if [[ ! -x "$executable" ]]; then
    echo "ERROR: executable not found: $executable" >&2
    exit 1
  fi
done
if ! command -v "$MPI_LAUNCHER" >/dev/null 2>&1; then
  echo "ERROR: MPI launcher not found: $MPI_LAUNCHER" >&2
  exit 1
fi
if [[ "$BACKGROUND_MODE" == T && ! -x /usr/sbin/taskpolicy ]]; then
  echo "ERROR: taskpolicy requested but unavailable." >&2
  exit 1
fi
if [[ -e "$RESULTS_DIR" ]]; then
  archive="${RESULTS_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RESULTS_DIR" "$archive"
  echo "Previous results preserved in $archive"
fi
mkdir -p "$RESULTS_DIR"

"$PYTHON" "$SCRIPT_DIR/extreme_skew.py" prepare \
  --source "$SI_TEST/coords_ideal.dat" --root "$RESULTS_DIR"

for representation in reduced extreme; do
  for ranks in 1 2; do
    directory="$RESULTS_DIR/${representation}_np${ranks}"
    cp "$SI_TEST/Si.ion" "$directory/Si.ion"
    cp "$SCRIPT_DIR/static.Conquest_input" "$directory/Conquest_input"
    echo "Running $representation cell on $ranks MPI rank(s)"
    (
      cd "$directory"
      if [[ "$BACKGROUND_MODE" == T ]]; then
        /usr/sbin/taskpolicy -b "$MPI_LAUNCHER" -np "$ranks" \
          "$CONQUEST_BIN" > mpi.log 2>&1
      else
        "$MPI_LAUNCHER" -np "$ranks" "$CONQUEST_BIN" > mpi.log 2>&1
      fi
    )
  done
done

"$PYTHON" "$SCRIPT_DIR/extreme_skew.py" analyse --root "$RESULTS_DIR"
