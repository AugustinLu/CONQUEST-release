#!/usr/bin/env bash
# Rutile TiO2: oxygen relaxation -> SCF -> pDOS -> HPKOT bands -> plot.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
POSTPROCESS_BIN="${POSTPROCESS_BIN:-$RELEASE_DIR/bin/PostProcessCQ}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
NP="${NP:-2}"
BACKGROUND_MODE="${BACKGROUND_MODE:-auto}"
RESULTS_DIR="${RESULTS_DIR:-$SCRIPT_DIR/results}"
BAND_POINTS="${BAND_POINTS:-35}"

if [[ "$BACKGROUND_MODE" == auto ]]; then
  [[ "$(uname -s)" == Darwin && -x /usr/sbin/taskpolicy ]] &&
    BACKGROUND_MODE=T || BACKGROUND_MODE=F
fi
if (( NP < 1 || NP > 2 )); then
  echo "ERROR: NP must be 1 or 2." >&2
  exit 2
fi
if [[ -e "$RESULTS_DIR" ]]; then
  archive="${RESULTS_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RESULTS_DIR" "$archive"
  echo "Previous results preserved in $archive"
fi
RELAX_DIR="$RESULTS_DIR/relax"
SCF_DIR="$RESULTS_DIR/scf"
PDOS_DIR="$RESULTS_DIR/pdos"
BAND_DIR="$RESULTS_DIR/bands"
mkdir -p "$RELAX_DIR" "$SCF_DIR" "$PDOS_DIR" "$BAND_DIR"

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
  cp "$SCRIPT_DIR/Ti.ion" "$1/Ti.ion"
  cp "$SCRIPT_DIR/O.ion" "$1/O.ion"
}
common_input() {
  cat <<'EOF'
IO.Coordinates              coords.dat
IO.FractionalAtomicCoords   T
General.NumberOfSpecies     2
General.PAOFromFiles        T
%block ChemicalSpeciesLabel
1 47.867 Ti Ti.ion
2 15.999 O  O.ion
%endblock
Grid.GridCutoff             100
DM.SolutionMethod           diagon
EOF
}

echo "[1/5] Rutile fixed-cell oxygen-coordinate relaxation"
stage_species "$RELAX_DIR"
cp "$SCRIPT_DIR/coords_relax_start.dat" "$RELAX_DIR/coords.dat"
{
  echo "IO.Title rutile_tio2_relax"
  common_input
  cat <<'EOF'
AtomMove.TypeOfRun          cg
AtomMove.OptCell            F
AtomMove.NumSteps           40
AtomMove.MaxForceTol        2.0e-4
AtomMove.ReuseDM            T
AtomMove.CGLineMin          backtrack
minE.SelfConsistent         T
minE.SCTolerance            1.0e-8
Diag.MPMesh                 T
Diag.GammaCentred           T
Diag.MPMeshX                3
Diag.MPMeshY                3
Diag.MPMeshZ                5
EOF
} > "$RELAX_DIR/Conquest_input"
run_conquest "$RELAX_DIR"

echo "[2/5] Converged SCF density"
stage_species "$SCF_DIR"
"$PYTHON" "$SCRIPT_DIR/symmetrize_rutile.py" \
  "$RELAX_DIR/coord_next.dat" "$SCF_DIR/coords.dat" \
  > "$SCF_DIR/symmetrize.log"
{
  echo "IO.Title rutile_tio2_scf"
  common_input
  cat <<'EOF'
AtomMove.TypeOfRun          static
IO.DumpChargeDensity        T
minE.SelfConsistent         T
minE.SCTolerance            1.0e-9
Diag.MPMesh                 T
Diag.GammaCentred           T
Diag.MPMeshX                4
Diag.MPMeshY                4
Diag.MPMeshZ                6
EOF
} > "$SCF_DIR/Conquest_input"
run_conquest "$SCF_DIR"
grep -q "Reached SCF tolerance" "$SCF_DIR/Conquest_out"

echo "[3/5] Fixed-density projected DOS"
stage_species "$PDOS_DIR"
cp "$SCF_DIR/coords.dat" "$PDOS_DIR/coords.dat"
cp "$SCF_DIR"/chden.* "$PDOS_DIR/"
{
  echo "IO.Title rutile_tio2_pdos"
  common_input
  cat <<'EOF'
AtomMove.TypeOfRun          static
minE.SelfConsistent         F
General.LoadRho             T
IO.writeDOS                 T
IO.write_proj_DOS           T
Diag.MPMesh                 T
Diag.GammaCentred           T
Diag.MPMeshX                5
Diag.MPMeshY                5
Diag.MPMeshZ                7
EOF
} > "$PDOS_DIR/Conquest_input"
run_conquest "$PDOS_DIR"
cat >> "$PDOS_DIR/Conquest_input" <<'EOF'
Process.Job                 pdos
Process.n_DOS              3001
Process.sigma_DOS          0.008
Process.WFRangeRelative    T
Process.min_DOS_E          -0.80
Process.max_DOS_E           0.60
Process.pDOS_l_resolved    T
EOF
(
  cd "$PDOS_DIR"
  "$MPI_LAUNCHER" -np 1 "$POSTPROCESS_BIN" > PostProcess_pdos.log 2>&1
)

echo "[4/5] HPKOT/SeeK-path band structure"
"$PYTHON" "$SCRIPT_DIR/generate_seekpath.py" "$SCF_DIR/coords.dat" \
  --output "$RESULTS_DIR/seekpath.json" > "$RESULTS_DIR/seekpath.log"
stage_species "$BAND_DIR"
cp "$SCF_DIR/coords.dat" "$BAND_DIR/coords.dat"
cp "$SCF_DIR"/chden.* "$BAND_DIR/"
{
  echo "IO.Title rutile_tio2_bands"
  common_input
  cat <<EOF
AtomMove.TypeOfRun          static
minE.SelfConsistent         F
General.LoadRho             T
Diag.KspaceLines            T
Diag.NumKptLines            9
Diag.NumKpts                $BAND_POINTS
%block Diag.KpointLines
0.0 0.0 0.0
0.0 0.5 0.0
0.0 0.5 0.0
0.5 0.5 0.0
0.5 0.5 0.0
0.0 0.0 0.0
0.0 0.0 0.0
0.0 0.0 0.5
0.0 0.0 0.5
0.0 0.5 0.5
0.0 0.5 0.5
0.5 0.5 0.5
0.5 0.5 0.5
0.0 0.0 0.5
0.0 0.5 0.0
0.0 0.5 0.5
0.5 0.5 0.0
0.5 0.5 0.5
%endblock
EOF
} > "$BAND_DIR/Conquest_input"
run_conquest "$BAND_DIR"

echo "[5/5] Plot and summarize"
mkdir -p "$RESULTS_DIR/.matplotlib"
MPLCONFIGDIR="$RESULTS_DIR/.matplotlib" "$PYTHON" "$SCRIPT_DIR/plot_rutile_band_pdos.py" \
  --bands "$BAND_DIR/eigenvalues.dat" --dos "$PDOS_DIR/DOS.dat" \
  --pdos-dir "$PDOS_DIR" --coords "$BAND_DIR/coords.dat" \
  --seekpath "$RESULTS_DIR/seekpath.json" --points-per-segment "$BAND_POINTS" \
  --relax-start "$RELAX_DIR/coords.dat" --relax-final "$RELAX_DIR/coord_next.dat" \
  --relax-output "$RELAX_DIR/Conquest_out" \
  --output "$RESULTS_DIR/rutile_tio2_band_pdos.png" \
  --summary "$RESULTS_DIR/summary.json"
