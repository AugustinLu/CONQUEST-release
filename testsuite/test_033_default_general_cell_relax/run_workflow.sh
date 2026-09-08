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
mkdir -p "$results_dir/method1" "$results_dir/method2"

for method in method1 method2; do
  case_dir="$results_dir/$method"
  cp "$script_dir/coords.dat" "$case_dir/coords.dat"
  cp "$release_dir/testsuite/test_001_bulk_Si_1proc_Diag/Si.ion" \
    "$case_dir/Si.ion"
done
cp "$script_dir/Conquest_input" "$results_dir/method1/Conquest_input"
cp "$script_dir/Conquest_input.method2" "$results_dir/method2/Conquest_input"

for method in method1 method2; do
  case_dir="$results_dir/$method"
  (
    cd "$case_dir"
    "$mpi_launcher" -np 1 "$conquest_bin" > mpi.log 2>&1
  )
  [[ -s "$case_dir/Conquest_out" ]]
done

"$python" "$script_dir/check_results.py" "$results_dir"
