#!/usr/bin/env bash
# Validate published 3R graphite in rhombohedral and hexagonal settings.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
BACKGROUND_MODE="${BACKGROUND_MODE:-F}"
RESULTS_DIR="${RESULTS_DIR:-$SCRIPT_DIR/results}"
CARBON_ION="$RELEASE_DIR/testsuite/test_010_graphite_monoclinic/C_PBE_SZP_CQ.ion"

for executable in "$CONQUEST_BIN" "$PYTHON"; do
  if [[ ! -x "$executable" ]]; then
    echo "ERROR: executable not found: $executable" >&2
    exit 1
  fi
done
if [[ ! -f "$CARBON_ION" ]]; then
  echo "ERROR: carbon ion file not found: $CARBON_ION" >&2
  exit 1
fi
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

"$PYTHON" "$SCRIPT_DIR/rhombohedral_graphite.py" prepare --root "$RESULTS_DIR"

for representation in rhombohedral hexagonal; do
  for ranks in 1 2; do
    directory="$RESULTS_DIR/${representation}_np${ranks}"
    cp "$CARBON_ION" "$directory/C_PBE_SZP_CQ.ion"
    cp "$SCRIPT_DIR/static.Conquest_input" "$directory/Conquest_input"
    echo "Running $representation 3R graphite on $ranks MPI rank(s)"
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

"$PYTHON" "$SCRIPT_DIR/rhombohedral_graphite.py" analyse \
  --root "$RESULTS_DIR"
