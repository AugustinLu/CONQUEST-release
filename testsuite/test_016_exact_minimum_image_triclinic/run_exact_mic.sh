#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
FC="${FC:-gfortran}"
RESULTS_DIR="${RESULTS_DIR:-$SCRIPT_DIR/results}"

if ! command -v "$FC" >/dev/null 2>&1; then
  echo "ERROR: Fortran compiler not found: $FC" >&2
  exit 1
fi
if [[ ! -f "$RELEASE_DIR/src/global_module.o" ]]; then
  echo "ERROR: build CONQUEST before running this source-level test." >&2
  exit 1
fi
mkdir -p "$RESULTS_DIR"
"$FC" -I"$RELEASE_DIR/src" \
  "$SCRIPT_DIR/test_exact_mic.f90" \
  "$RELEASE_DIR/src/global_module.o" \
  -o "$RESULTS_DIR/test_exact_mic"
"$RESULTS_DIR/test_exact_mic" | tee "$RESULTS_DIR/test_exact_mic.log"
