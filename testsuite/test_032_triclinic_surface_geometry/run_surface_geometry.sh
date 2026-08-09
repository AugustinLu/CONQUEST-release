#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
release_dir="$(cd -- "$script_dir/../.." && pwd)"
fc="${FC:-gfortran}"
results_dir="${RESULTS_DIR:-$script_dir/results}"

mkdir -p "$results_dir"
"$fc" -I"$release_dir/src" \
  "$script_dir/test_surface_geometry.f90" \
  "$release_dir/src/global_module.o" \
  -o "$results_dir/test_surface_geometry"
"$results_dir/test_surface_geometry" | tee "$results_dir/test_surface_geometry.log"
