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
mkdir -p "$results_dir/native" "$results_dir/restart"

cp "$release_dir/testsuite/test_001_bulk_Si_1proc_Diag/Si.ion" \
  "$results_dir/native/Si.ion"
cp "$release_dir/testsuite/test_001_bulk_Si_1proc_Diag/Si.ion" \
  "$results_dir/restart/Si.ion"
cp "$script_dir/native.Conquest_input" "$results_dir/native/Conquest_input"
cp "$script_dir/coords.dat" "$results_dir/native/coords.dat"
cp "$script_dir/template.pdb" "$results_dir/native/template.pdb"

(
  cd "$results_dir/native"
  "$mpi_launcher" -np 1 "$conquest_bin" > mpi.log 2>&1
)
grep -q "Reached SCF tolerance" "$results_dir/native/Conquest_out"
grep -q '^SCALE1' "$results_dir/native/output.pdb"

cp "$script_dir/restart.Conquest_input" "$results_dir/restart/Conquest_input"
cp "$results_dir/native/output.pdb" "$results_dir/restart/restart.pdb"
(
  cd "$results_dir/restart"
  "$mpi_launcher" -np 1 "$conquest_bin" > mpi.log 2>&1
)
grep -q "Reached SCF tolerance" "$results_dir/restart/Conquest_out"

"$python" "$script_dir/check_roundtrip.py" \
  --coords "$script_dir/coords.dat" \
  --native-pdb "$results_dir/native/output.pdb" \
  --restart-pdb "$results_dir/restart/output.pdb"
