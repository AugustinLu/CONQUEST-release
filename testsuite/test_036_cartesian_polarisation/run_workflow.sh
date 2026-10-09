#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
"${PYTHON:-python3}" "$script_dir/check_rotation.py" \
    --binary "${CONQUEST_BIN:-$script_dir/../../bin/Conquest}" \
    --results "${RESULTS_DIR:-$(mktemp -d /tmp/cq-polarisation.XXXXXX)}"
