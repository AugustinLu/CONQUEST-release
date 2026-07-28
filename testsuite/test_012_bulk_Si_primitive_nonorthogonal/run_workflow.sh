#!/usr/bin/env bash
# Primitive Si: atomic relaxation -> SCF -> l-resolved pDOS -> bands -> plot.
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
SCF_MESH="${SCF_MESH:-8}"
PDOS_MESH="${PDOS_MESH:-10}"
BAND_POINTS="${BAND_POINTS:-50}"
GRID_CUTOFF="${GRID_CUTOFF:-80}"

if [[ "$BACKGROUND_MODE" == auto ]]; then
  if [[ "$(uname -s)" == Darwin && -x /usr/sbin/taskpolicy ]]; then
    BACKGROUND_MODE=T
  else
    BACKGROUND_MODE=F
  fi
fi

if [[ "$BACKGROUND_MODE" == T ]]; then
  max_ranks=2
else
  max_ranks=2
fi
if (( NP < 1 || NP > max_ranks )); then
  echo "ERROR: primitive Si has two atoms; NP must be between 1 and 2." >&2
  exit 2
fi

for executable in "$CONQUEST_BIN" "$POSTPROCESS_BIN" "$PYTHON"; do
  if [[ ! -x "$executable" ]]; then
    echo "ERROR: executable not found: $executable" >&2
    exit 1
  fi
done
if ! command -v "$MPI_LAUNCHER" >/dev/null 2>&1; then
  echo "ERROR: MPI launcher not found: $MPI_LAUNCHER" >&2
  exit 1
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
  if [[ ! -s "$directory/Conquest_out" ]]; then
    echo "ERROR: CONQUEST did not produce output in $directory" >&2
    exit 1
  fi
}

stage_species() {
  cp "$SCRIPT_DIR/Si.ion" "$1/Si.ion"
}

validate_input() {
  local directory="$1"
  if command -v conquest-input-check >/dev/null 2>&1; then
    (
      cd "$directory"
      conquest-input-check > input-check.log 2>&1
    )
    if grep -Eq "^Error:" "$directory/input-check.log"; then
      cat "$directory/input-check.log" >&2
      exit 1
    fi
  fi
}

write_common_input() {
  cat <<EOF
IO.Coordinates              coords.dat
IO.FractionalAtomicCoords   T
General.NumberOfSpecies     1
General.PAOFromFiles        T
%block ChemicalSpeciesLabel
1 28.086 Si Si.ion
%endblock
Grid.GridCutoff             $GRID_CUTOFF
DM.SolutionMethod           diagon
EOF
}

echo "Primitive Si nonorthogonal validation"
echo "  MPI ranks       : $NP"
echo "  taskpolicy -b   : $BACKGROUND_MODE"
echo "  results         : $RESULTS_DIR"

echo "[1/5] Fixed-cell atomic relaxation from a displaced basis atom"
stage_species "$RELAX_DIR"
cp "$SCRIPT_DIR/coords_relax_start.dat" "$RELAX_DIR/coords.dat"
{
  echo "IO.Title                    primitive_si_relax"
  write_common_input
  cat <<EOF
AtomMove.TypeOfRun          cg
AtomMove.OptCell            F
AtomMove.NumSteps           40
AtomMove.MaxForceTol        1.0e-4
AtomMove.ReuseDM            T
AtomMove.CGLineMin          backtrack
minE.SelfConsistent         T
minE.SCTolerance            1.0e-7
Diag.MPMesh                 T
Diag.GammaCentred           T
Diag.MPMeshX                4
Diag.MPMeshY                4
Diag.MPMeshZ                4
EOF
} > "$RELAX_DIR/Conquest_input"
validate_input "$RELAX_DIR"
run_conquest "$RELAX_DIR"
if [[ ! -s "$RELAX_DIR/coord_next.dat" ]]; then
  echo "ERROR: relaxation did not write coord_next.dat" >&2
  exit 1
fi

echo "[2/5] Converged self-consistent density"
stage_species "$SCF_DIR"
cp "$RELAX_DIR/coord_next.dat" "$SCF_DIR/coords.dat"
{
  echo "IO.Title                    primitive_si_scf"
  write_common_input
  cat <<EOF
AtomMove.TypeOfRun          static
IO.DumpChargeDensity        T
minE.SelfConsistent         T
minE.SCTolerance            1.0e-8
Diag.MPMesh                 T
Diag.GammaCentred           T
Diag.MPMeshX                $SCF_MESH
Diag.MPMeshY                $SCF_MESH
Diag.MPMeshZ                $SCF_MESH
EOF
} > "$SCF_DIR/Conquest_input"
validate_input "$SCF_DIR"
run_conquest "$SCF_DIR"
grep -q "Reached SCF tolerance" "$SCF_DIR/Conquest_out"

echo "[3/5] Fixed-density l-resolved projected DOS"
stage_species "$PDOS_DIR"
cp "$SCF_DIR/coords.dat" "$PDOS_DIR/coords.dat"
cp "$SCF_DIR"/chden.* "$PDOS_DIR/"
{
  echo "IO.Title                    primitive_si_pdos"
  write_common_input
  cat <<EOF
AtomMove.TypeOfRun          static
minE.SelfConsistent         F
General.LoadRho             T
IO.writeDOS                 T
IO.write_proj_DOS           T
Diag.MPMesh                 T
Diag.GammaCentred           T
Diag.MPMeshX                $PDOS_MESH
Diag.MPMeshY                $PDOS_MESH
Diag.MPMeshZ                $PDOS_MESH
EOF
} > "$PDOS_DIR/Conquest_input"
validate_input "$PDOS_DIR"
run_conquest "$PDOS_DIR"
cat >> "$PDOS_DIR/Conquest_input" <<EOF

Process.Job                 pdos
Process.n_DOS               2401
Process.sigma_DOS           0.006
Process.WFRangeRelative     T
Process.min_DOS_E           -0.60
Process.max_DOS_E            0.40
Process.pDOS_l_resolved     T
EOF
(
  cd "$PDOS_DIR"
  if [[ "$BACKGROUND_MODE" == T ]]; then
    /usr/sbin/taskpolicy -b "$MPI_LAUNCHER" -np 1 "$POSTPROCESS_BIN" \
      > PostProcess_pdos.log 2>&1
  else
    "$MPI_LAUNCHER" -np 1 "$POSTPROCESS_BIN" > PostProcess_pdos.log 2>&1
  fi
)

echo "[4/5] HPKOT/SeeK-path band structure"
"$PYTHON" "$SCRIPT_DIR/generate_seekpath.py" "$SCRIPT_DIR/coords_ideal.dat" \
  --output "$RESULTS_DIR/seekpath.json" > "$RESULTS_DIR/seekpath.log"
stage_species "$BAND_DIR"
cp "$SCF_DIR/coords.dat" "$BAND_DIR/coords.dat"
cp "$SCF_DIR"/chden.* "$BAND_DIR/"
{
  echo "IO.Title                    primitive_si_bands"
  write_common_input
  cat <<EOF
AtomMove.TypeOfRun          static
minE.SelfConsistent         F
General.LoadRho             T
Diag.KspaceLines            T
Diag.NumKptLines            6
Diag.NumKpts                $BAND_POINTS
%block Diag.KpointLines
0.000 0.000 0.000
0.500 0.000 0.500
0.500 0.000 0.500
0.625 0.250 0.625
0.375 0.375 0.750
0.000 0.000 0.000
0.000 0.000 0.000
0.500 0.500 0.500
0.500 0.500 0.500
0.500 0.250 0.750
0.500 0.250 0.750
0.500 0.000 0.500
%endblock
EOF
} > "$BAND_DIR/Conquest_input"
validate_input "$BAND_DIR"
run_conquest "$BAND_DIR"

echo "[5/5] Plot and summarize"
mkdir -p "$RESULTS_DIR/.matplotlib"
MPLCONFIGDIR="$RESULTS_DIR/.matplotlib" "$PYTHON" "$SCRIPT_DIR/plot_si_band_pdos.py" \
  --bands "$BAND_DIR/eigenvalues.dat" \
  --dos "$PDOS_DIR/DOS.dat" \
  --pdos-dir "$PDOS_DIR" \
  --coords "$BAND_DIR/coords.dat" \
  --seekpath "$RESULTS_DIR/seekpath.json" \
  --points-per-segment "$BAND_POINTS" \
  --relax-start "$RELAX_DIR/coords.dat" \
  --relax-final "$RELAX_DIR/coord_next.dat" \
  --relax-output "$RELAX_DIR/Conquest_out" \
  --output "$RESULTS_DIR/primitive_si_band_pdos.png" \
  --summary "$RESULTS_DIR/summary.json"

echo "Completed: $RESULTS_DIR"
