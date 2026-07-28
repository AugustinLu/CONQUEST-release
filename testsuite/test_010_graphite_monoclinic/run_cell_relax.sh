#!/usr/bin/env bash
# Full symmetric-strain relaxation of four-atom AB graphite.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
NP="${NP:-2}"
BACKGROUND_MODE="${BACKGROUND_MODE:-auto}"
RUN_DIR="${RUN_DIR:-$SCRIPT_DIR/cell_relax_results}"

if [[ "$BACKGROUND_MODE" == auto ]]; then
  if [[ "$(uname -s)" == Darwin && -x /usr/sbin/taskpolicy ]]; then
    BACKGROUND_MODE=T
  else
    BACKGROUND_MODE=F
  fi
fi
if (( NP < 1 || NP > 2 )); then
  echo "ERROR: NP must be 1 or 2." >&2
  exit 2
fi
if [[ ! -x "$CONQUEST_BIN" ]]; then
  echo "ERROR: executable not found: $CONQUEST_BIN" >&2
  exit 1
fi
if [[ -e "$RUN_DIR" ]]; then
  archive="${RUN_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RUN_DIR" "$archive"
  echo "Previous result preserved in $archive"
fi
mkdir -p "$RUN_DIR"
cp "$SCRIPT_DIR/coords_cell_relax_start.dat" "$RUN_DIR/coords.dat"
cp "$SCRIPT_DIR/cell_relax.Conquest_input" "$RUN_DIR/Conquest_input"
cp "$SCRIPT_DIR/C_PBE_SZP_CQ.ion" "$RUN_DIR/C.ion"

echo "Graphite full-cell symmetric-strain relaxation"
echo "  MPI ranks       : $NP"
echo "  taskpolicy -b   : $BACKGROUND_MODE"
echo "  result          : $RUN_DIR"
(
  cd "$RUN_DIR"
  if [[ "$BACKGROUND_MODE" == T ]]; then
    /usr/sbin/taskpolicy -b "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" \
      > mpi.log 2>&1
  else
    "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" > mpi.log 2>&1
  fi
)

if ! grep -q "combined ionic and cell steps" "$RUN_DIR/Conquest_out"; then
  echo "ERROR: coupled atom/cell relaxation did not converge; see $RUN_DIR/Conquest_out" >&2
  exit 1
fi
echo "Coupled atom/cell relaxation converged."
echo "Final cell and atoms: $RUN_DIR/UpdatedAtoms.dat"
