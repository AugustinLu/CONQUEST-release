#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bash "$script_dir/run_unit.sh"
"${PYTHON:-python3}" "$script_dir/check_relaxation.py" \
    --binary "${CONQUEST_BIN:-$script_dir/../../bin/Conquest}" \
    --results "${RESULTS_DIR:-$(mktemp -d /tmp/cq-constraints.XXXXXX)}"
