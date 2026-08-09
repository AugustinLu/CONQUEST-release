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
mkdir -p "$results_dir/axis_aligned" "$results_dir/general"

cp "$release_dir/testsuite/test_001_bulk_Si_1proc_Diag/Si.ion" \
  "$results_dir/axis_aligned/Si.ion"
cp "$release_dir/testsuite/test_001_bulk_Si_1proc_Diag/Si.ion" \
  "$results_dir/general/Si.ion"
cp "$script_dir/Conquest_input" "$results_dir/axis_aligned/Conquest_input"
cp "$script_dir/Conquest_input" "$results_dir/general/Conquest_input"
cp "$script_dir/coords_axis_aligned.dat" "$results_dir/axis_aligned/coords.dat"
cp "$script_dir/coords_general.dat" "$results_dir/general/coords.dat"

for case_dir in "$results_dir/axis_aligned" "$results_dir/general"; do
  (
    cd "$case_dir"
    "$mpi_launcher" -np 1 "$conquest_bin" > mpi.log 2>&1
  )
  grep -q "Reached SCF tolerance" "$case_dir/Conquest_out"
done

"$python" "$script_dir/check_full_stress.py" "$results_dir"
