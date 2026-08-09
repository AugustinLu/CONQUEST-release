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
mkdir -p "$results_dir"
cp "$script_dir/Conquest_input" "$results_dir/Conquest_input"
cp "$script_dir/coords.dat" "$results_dir/coords.dat"
cp "$release_dir/testsuite/test_001_bulk_Si_1proc_Diag/Si.ion" \
  "$results_dir/Si.ion"

(
  cd "$results_dir"
  "$mpi_launcher" -np 1 "$conquest_bin" > mpi.log 2>&1
)
grep -q "Reached SCF tolerance" "$results_dir/Conquest_out"
"$python" "$script_dir/check_sampling.py" "$results_dir"
