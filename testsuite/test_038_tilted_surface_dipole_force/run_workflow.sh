#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
release_dir="$(cd -- "$script_dir/../.." && pwd)"
conquest_bin="${CONQUEST_BIN:-$release_dir/bin/Conquest}"
mpi_launcher="${MPI_LAUNCHER:-mpirun}"
python="${PYTHON:-python3}"
results_dir="${RESULTS_DIR:-$script_dir/results}"
ion_dir="$release_dir/testsuite/test_008_surface_dipole"

if [[ -e "$results_dir" ]]; then
  archive="${results_dir}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$results_dir" "$archive"
fi

"$python" "$script_dir/prepare_cases.py" "$results_dir"
for case_name in c0 a1p a1m a2p a2m; do
  case_dir="$results_dir/$case_name"
  cp "$script_dir/Conquest_input" "$case_dir/Conquest_input"
  cp "$ion_dir/O.ion" "$ion_dir/H.ion" "$case_dir/"
  (
    cd "$case_dir"
    "$mpi_launcher" -np 1 "$conquest_bin" > mpi.log 2>&1
  )
done

"$python" "$script_dir/check_forces.py" "$results_dir"
