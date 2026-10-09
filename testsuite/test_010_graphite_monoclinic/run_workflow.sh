#!/usr/bin/env bash
# Run the three maintained carbon acceptance workflows as one suite entrypoint.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bash "$script_dir/run_cell_relax.sh"
bash "$script_dir/run_graphite_hcp.sh"
bash "$script_dir/run_graphene.sh"
