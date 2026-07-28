#!/usr/bin/env bash
# 2H-MoS2 internal relaxation -> SCF -> pDOS -> HPKOT bands -> plot.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
POSTPROCESS_BIN="${POSTPROCESS_BIN:-$RELEASE_DIR/bin/PostProcessCQ}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
NP="${NP:-2}"
BACKGROUND_MODE="${BACKGROUND_MODE:-F}"
RESULTS_DIR="${RESULTS_DIR:-$SCRIPT_DIR/results/workflow}"
BAND_POINTS=35

if (( NP < 1 || NP > 4 )); then
  echo "ERROR: this six-atom test permits one to four MPI ranks." >&2
  exit 2
fi
if [[ ! -x "$CONQUEST_BIN" || ! -x "$POSTPROCESS_BIN" ]]; then
  echo "ERROR: CONQUEST or PostProcessCQ executable is missing." >&2
  exit 2
fi
if [[ -e "$RESULTS_DIR" ]]; then
  archive="${RESULTS_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RESULTS_DIR" "$archive"
  echo "Previous workflow preserved in $archive"
fi
RELAX_DIR="$RESULTS_DIR/relax"
SCF_DIR="$RESULTS_DIR/scf"
PDOS_DIR="$RESULTS_DIR/pdos"
BAND_DIR="$RESULTS_DIR/bands"
mkdir -p "$SCF_DIR" "$PDOS_DIR" "$BAND_DIR" "$RESULTS_DIR/.matplotlib"

run_conquest() {
  local directory="$1"
  (
    cd "$directory"
    if [[ "$BACKGROUND_MODE" == T ]]; then
      /usr/sbin/taskpolicy -b "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" \
        > mpi.log 2>&1
    else
      "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" > mpi.log 2>&1
    fi
  )
  [[ -s "$directory/Conquest_out" ]]
}

stage_species() {
  cp "$SCRIPT_DIR/Mo.ion" "$1/Mo.ion"
  cp "$SCRIPT_DIR/S.ion" "$1/S.ion"
}

echo "[1/5] Symmetry-preserving sulfur internal-coordinate relaxation"
RUN_DIR="$RELAX_DIR" NP="$NP" BACKGROUND_MODE="$BACKGROUND_MODE" \
  "$SCRIPT_DIR/run_internal_relax.sh"

echo "[2/5] Converged relaxed-cell SCF density"
stage_species "$SCF_DIR"
cp "$RELAX_DIR/coord_next.dat" "$SCF_DIR/coords.dat"
cp "$SCRIPT_DIR/scf.Conquest_input" "$SCF_DIR/Conquest_input"
run_conquest "$SCF_DIR"
grep -q "Reached SCF tolerance" "$SCF_DIR/Conquest_out"
grep -Eq "Number of electrons[[:space:]]*=[[:space:]]*52\\.0" \
  "$SCF_DIR/Conquest_out"

echo "[3/5] Fixed-density l-resolved projected DOS"
stage_species "$PDOS_DIR"
cp "$SCF_DIR/coords.dat" "$PDOS_DIR/coords.dat"
cp "$SCF_DIR"/chden.* "$PDOS_DIR/"
cp "$SCRIPT_DIR/pdos.Conquest_input" "$PDOS_DIR/Conquest_input"
run_conquest "$PDOS_DIR"
cp "$SCRIPT_DIR/pdos_postprocess.Conquest_input" "$PDOS_DIR/Conquest_input"
(
  cd "$PDOS_DIR"
  "$MPI_LAUNCHER" -np 1 "$POSTPROCESS_BIN" > PostProcess_pdos.log 2>&1
)
[[ -s "$PDOS_DIR/DOS.dat" ]]
[[ "$(find "$PDOS_DIR" -maxdepth 1 -name 'Atom*DOS_l.dat' | wc -l)" -eq 6 ]]

echo "[4/5] HPKOT/SeeK-path fixed-density band structure"
"$PYTHON" "$SCRIPT_DIR/generate_seekpath.py" "$SCF_DIR/coords.dat" \
  --output "$RESULTS_DIR/seekpath.json" > "$RESULTS_DIR/seekpath.log"
grep -q '"spacegroup_number": 194' "$RESULTS_DIR/seekpath.json"
stage_species "$BAND_DIR"
cp "$SCF_DIR/coords.dat" "$BAND_DIR/coords.dat"
cp "$SCF_DIR"/chden.* "$BAND_DIR/"
cp "$SCRIPT_DIR/bands.Conquest_input" "$BAND_DIR/Conquest_input"
run_conquest "$BAND_DIR"
[[ -s "$BAND_DIR/eigenvalues.dat" ]]

echo "[5/5] Zero-width-branch band/pDOS plot and summary"
MPLCONFIGDIR="$RESULTS_DIR/.matplotlib" "$PYTHON" \
  "$SCRIPT_DIR/plot_mos2_band_pdos.py" \
  --bands "$BAND_DIR/eigenvalues.dat" \
  --dos "$PDOS_DIR/DOS.dat" \
  --pdos-dir "$PDOS_DIR" \
  --seekpath "$RESULTS_DIR/seekpath.json" \
  --points-per-segment "$BAND_POINTS" \
  --relax-start "$RELAX_DIR/coords.dat" \
  --relax-final "$RELAX_DIR/coord_next.dat" \
  --relax-output "$RELAX_DIR/Conquest_out" \
  --output "$RESULTS_DIR/bulk_2h_mos2_band_pdos.png" \
  --summary "$RESULTS_DIR/summary.json"

echo "PASS: bulk 2H-MoS2 relaxation, SCF, pDOS, and HPKOT bands completed."
