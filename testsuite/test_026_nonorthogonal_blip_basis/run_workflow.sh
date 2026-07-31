#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
RESULTS_DIR="${RESULTS_DIR:-$SCRIPT_DIR/results}"
SI_ION="$RELEASE_DIR/testsuite/test_001_bulk_Si_1proc_Diag/Si.ion"

if [[ ! -x "$CONQUEST_BIN" ]]; then
  echo "ERROR: executable not found: $CONQUEST_BIN" >&2
  exit 1
fi
if [[ ! -f "$SI_ION" ]]; then
  echo "ERROR: Si ion file not found: $SI_ION" >&2
  exit 1
fi
if ! command -v "$MPI_LAUNCHER" >/dev/null 2>&1; then
  echo "ERROR: MPI launcher not found: $MPI_LAUNCHER" >&2
  exit 1
fi

if [[ -e "$RESULTS_DIR" ]]; then
  archive="${RESULTS_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RESULTS_DIR" "$archive"
  echo "Previous results preserved in $archive"
fi
mkdir -p "$RESULTS_DIR"
for ranks in 1 2; do
  directory="$RESULTS_DIR/nonorthogonal_np${ranks}"
  mkdir -p "$directory"
  cp "$SCRIPT_DIR/Conquest_input" "$directory/Conquest_input"
  cp "$SCRIPT_DIR/coords.dat" "$directory/coords.dat"
  cp "$SI_ION" "$directory/Si.ion"
  (
    cd "$directory"
    "$MPI_LAUNCHER" -np "$ranks" "$CONQUEST_BIN"
  )
done

python3 "$SCRIPT_DIR/check_nonorthogonal_blip.py" "$RESULTS_DIR"
