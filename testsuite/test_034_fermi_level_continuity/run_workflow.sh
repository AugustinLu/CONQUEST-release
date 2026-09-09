#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
release_dir="$(cd -- "$script_dir/../.." && pwd)"
conquest_bin="${CONQUEST_BIN:-$release_dir/bin/Conquest}"
mpi_launcher="${MPI_LAUNCHER:-mpirun}"
python="${PYTHON:-python3}"
results_dir="${RESULTS_DIR:-$script_dir/results}"

if [[ -e "$results_dir" ]]; then
  archive="${results_dir}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$results_dir" "$archive"
fi

"$python" "$script_dir/prepare_cases.py" "$results_dir"
for microstrain in 184 185 186 187; do
  case_dir="$results_dir/d$microstrain"
  cp "$script_dir/Conquest_input" "$case_dir/Conquest_input"
  cp "$release_dir/testsuite/test_012_bulk_Si_primitive_nonorthogonal/Si.ion" \
    "$case_dir/Si.ion"
  (
    cd "$case_dir"
    "$mpi_launcher" -np 1 "$conquest_bin" > mpi.log 2>&1
  )
done

"$python" "$script_dir/check_continuity.py" "$results_dir"
