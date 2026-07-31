#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
RELEASE_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
NP=${NP:-1}
RESULT_DIR="$SCRIPT_DIR/results/orthorhombic_np${NP}"

if [[ ! -x "$RELEASE_DIR/bin/Conquest" ]]; then
  echo "Missing executable: $RELEASE_DIR/bin/Conquest" >&2
  exit 1
fi
if [[ ! -f "$SCRIPT_DIR/../test_001_bulk_Si_1proc_Diag/Si.ion" ]]; then
  echo "Missing Si ion file from test 001" >&2
  exit 1
fi

mkdir -p "$RESULT_DIR"
cp "$SCRIPT_DIR/Conquest_input" "$RESULT_DIR/"
cp "$SCRIPT_DIR/coords.dat" "$RESULT_DIR/"
cp "$SCRIPT_DIR/../test_001_bulk_Si_1proc_Diag/Si.ion" "$RESULT_DIR/"

(
  cd "$RESULT_DIR"
  mpirun -np "$NP" "$RELEASE_DIR/bin/Conquest"
)

python3 "$SCRIPT_DIR/check_blip_smoke.py" "$RESULT_DIR/Conquest_out"
