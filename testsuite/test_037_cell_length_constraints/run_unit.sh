#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "$script_dir/../.." && pwd)"
build_dir="$(mktemp -d "${TMPDIR:-/tmp}/cq-length-gradient.XXXXXX")"
trap 'rm -rf "$build_dir"' EXIT
cd "$build_dir"
"${FC:-gfortran}" -O0 -g -fcheck=all -o test_gradient \
    "$repo_dir/src/datatypes_module.f90" "$repo_dir/src/cell_relaxation_module.f90" \
    "$script_dir/test_gradient.f90"
./test_gradient
