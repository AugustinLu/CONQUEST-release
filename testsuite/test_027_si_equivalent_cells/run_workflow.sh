#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
release_dir="$(cd -- "$script_dir/../.." && pwd)"
conquest_bin="${CONQUEST_BIN:-$release_dir/bin/Conquest}"
mpi_launcher="${MPI_LAUNCHER:-mpirun}"
python="${PYTHON:-python3}"
results_dir="${RESULTS_DIR:-$script_dir/results}"
si_ion="$release_dir/testsuite/test_001_bulk_Si_1proc_Diag/Si.ion"

if [[ ! -x "$conquest_bin" ]]; then
  echo "ERROR: executable not found: $conquest_bin" >&2
  exit 1
fi
if [[ ! -f "$si_ion" ]]; then
  echo "ERROR: Si ion file not found: $si_ion" >&2
  exit 1
fi
if ! command -v "$mpi_launcher" >/dev/null 2>&1; then
  echo "ERROR: MPI launcher not found: $mpi_launcher" >&2
  exit 1
fi

if [[ -e "$results_dir" ]]; then
  archive="${results_dir}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$results_dir" "$archive"
  echo "Previous results preserved in $archive"
fi
mkdir -p "$results_dir"

for case_name in cubic primitive; do
  case_dir="$results_dir/$case_name"
  mkdir -p "$case_dir"
  cp "$script_dir/$case_name.Conquest_input" "$case_dir/Conquest_input"
  cp "$script_dir/coords_$case_name.in" "$case_dir/coords_$case_name.in"
  cp "$si_ion" "$case_dir/Si.ion"
  echo "Running $case_name Si cell with one MPI rank"
  (
    cd "$case_dir"
    /usr/bin/nice -n 10 "$mpi_launcher" -np 1 "$conquest_bin"
  )
done

"$python" "$script_dir/check_equivalence.py" "$results_dir"
