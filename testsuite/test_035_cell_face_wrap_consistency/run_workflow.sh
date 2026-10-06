#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
release_dir="$(cd -- "$script_dir/../.." && pwd)"
conquest_bin="${CONQUEST_BIN:-$release_dir/bin/Conquest}"
mpi_launcher="${MPI_LAUNCHER:-mpirun}"
python="${PYTHON:-python3}"
np="${NP:-2}"
results_dir="${RESULTS_DIR:-$script_dir/results}"

if (( np < 1 || np > 4 )); then
  echo "ERROR: NP must be between 1 and 4." >&2
  exit 2
fi
if [[ -e "$results_dir" ]]; then
  archive="${results_dir}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$results_dir" "$archive"
fi

for case_name in below_face above_face; do
  case_dir="$results_dir/$case_name"
  mkdir -p "$case_dir"
  cp "$release_dir/testsuite/test_001_bulk_Si_1proc_Diag/Si.ion" "$case_dir/Si.ion"
  cp "$script_dir/Conquest_input" "$case_dir/Conquest_input"
  cp "$script_dir/coords_${case_name}.dat" "$case_dir/coords.dat"
  (
    cd "$case_dir"
    "$mpi_launcher" -np "$np" "$conquest_bin" > mpi.log 2>&1
  )
  grep -q "Reached SCF tolerance" "$case_dir/Conquest_out"
done

"$python" "$script_dir/check_face_wrap.py" "$results_dir"
