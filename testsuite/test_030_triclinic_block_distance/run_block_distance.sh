#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
release_dir="$(cd -- "$script_dir/../.." && pwd)"
fc="${FC:-gfortran}"
results_dir="${RESULTS_DIR:-$script_dir/results}"

mkdir -p "$results_dir"
"$fc" -I"$release_dir/src" \
  "$script_dir/test_block_distance.f90" \
  "$release_dir/src/global_module.o" \
  -o "$results_dir/test_block_distance"
"$results_dir/test_block_distance" | tee "$results_dir/test_block_distance.log"
