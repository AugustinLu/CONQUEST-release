#!/usr/bin/env bash
# Compare equivalent monoclinic cells on one and two MPI ranks.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
BACKGROUND_MODE="${BACKGROUND_MODE:-F}"
RUN_DIR="${RUN_DIR:-$SCRIPT_DIR/results/equivalent_cell_invariance}"

if [[ ! -x "$CONQUEST_BIN" ]]; then
  echo "ERROR: executable not found: $CONQUEST_BIN" >&2
  exit 1
fi
if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: Python executable not found: $PYTHON" >&2
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
if [[ -e "$RUN_DIR" ]]; then
  archive="${RUN_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RUN_DIR" "$archive"
  echo "Previous invariance check preserved in $archive"
fi

mkdir -p "$RUN_DIR"
"$PYTHON" "$SCRIPT_DIR/equivalent_cell_invariance.py" prepare \
  --base "$SCRIPT_DIR/coords.dat" --root "$RUN_DIR" \
  > "$RUN_DIR/prepare.log"

for representation in base sheared; do
  for ranks in 1 2; do
    directory="$RUN_DIR/${representation}_np${ranks}"
    cp "$SCRIPT_DIR/HfCQ.ion" "$directory/HfCQ.ion"
    cp "$SCRIPT_DIR/OCQ.ion" "$directory/OCQ.ion"
    cp "$SCRIPT_DIR/equivalent_cell_static.Conquest_input" \
      "$directory/Conquest_input"
    echo "Running ${representation} representation on ${ranks} MPI rank(s)"
    (
      cd "$directory"
      if [[ "$BACKGROUND_MODE" == T ]]; then
        /usr/sbin/taskpolicy -b "$MPI_LAUNCHER" -np "$ranks" "$CONQUEST_BIN" \
          > mpi.log 2>&1
      else
        "$MPI_LAUNCHER" -np "$ranks" "$CONQUEST_BIN" > mpi.log 2>&1
      fi
    )
    grep -q "Reached SCF tolerance" "$directory/Conquest_out"
    grep -q "Ewald total energy" "$directory/Conquest_out"
    grep -q "force: Total stress:" "$directory/Conquest_out"
  done
done

"$PYTHON" "$SCRIPT_DIR/equivalent_cell_invariance.py" analyse \
  --root "$RUN_DIR" --summary "$RUN_DIR/summary.json"
