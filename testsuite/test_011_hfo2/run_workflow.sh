#!/usr/bin/env bash
# Monoclinic HfO2: SCF -> l-resolved pDOS -> HPKOT bands -> plot.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
POSTPROCESS_BIN="${POSTPROCESS_BIN:-$RELEASE_DIR/bin/PostProcessCQ}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
NP="${NP:-2}"
BACKGROUND_MODE="${BACKGROUND_MODE:-F}"
RESULTS_DIR="${RESULTS_DIR:-$SCRIPT_DIR/results/electronic}"
COORDS_SOURCE="${COORDS_SOURCE:-$SCRIPT_DIR/coords.dat}"
BAND_POINTS="${BAND_POINTS:-24}"
K_MESH="${K_MESH:-3}"

if (( NP < 1 || NP > 2 )); then
  echo "ERROR: this maintained workflow permits one or two MPI ranks." >&2
  exit 2
fi
for executable in "$CONQUEST_BIN" "$POSTPROCESS_BIN" "$PYTHON"; do
  if [[ ! -x "$executable" ]]; then
    echo "ERROR: executable not found: $executable" >&2
    exit 2
  fi
done
if [[ ! -s "$COORDS_SOURCE" ]]; then
  echo "ERROR: coordinate source not found: $COORDS_SOURCE" >&2
  exit 2
fi
if [[ "$BACKGROUND_MODE" == T && ! -x /usr/sbin/taskpolicy ]]; then
  echo "ERROR: taskpolicy requested but unavailable." >&2
  exit 2
fi
if [[ -e "$RESULTS_DIR" ]]; then
  archive="${RESULTS_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RESULTS_DIR" "$archive"
  echo "Previous results preserved in $archive"
fi
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

run_postprocess() {
  local directory="$1"
  (
    cd "$directory"
    if [[ "$BACKGROUND_MODE" == T ]]; then
      /usr/sbin/taskpolicy -b "$MPI_LAUNCHER" -np 1 "$POSTPROCESS_BIN" \
        > PostProcess_pdos.log 2>&1
    else
      "$MPI_LAUNCHER" -np 1 "$POSTPROCESS_BIN" \
        > PostProcess_pdos.log 2>&1
    fi
  )
}

stage_species() {
  # PostProcessCQ reconstructs the ion filename from the chemical symbol.
  cp "$SCRIPT_DIR/HfCQ.ion" "$1/Hf.ion"
  cp "$SCRIPT_DIR/OCQ.ion" "$1/O.ion"
}

common_input() {
  cat <<'EOF'
IO.Coordinates              coords.dat
IO.FractionalAtomicCoords   T
General.NumberOfSpecies     2
General.DifferentFunctional T
General.FunctionalType      101
General.PAOFromFiles        T
%block ChemicalSpeciesLabel
1 178.4900 Hf Hf.ion
2 15.9994 O  O.ion
%endblock
Basis.BasisSet              PAOs
Grid.GridCutoff             100
DM.SolutionMethod           diagon
SC.KerkerPreCondition       T
SC.LinearMixingFactor       0.35
SC.MaxIters                 250
EOF
}

echo "[1/4] Converged PBE/DZP SCF density on monoclinic HfO2"
stage_species "$SCF_DIR"
cp "$COORDS_SOURCE" "$SCF_DIR/coords.dat"
{
  echo "IO.Title monoclinic_hfo2_scf"
  common_input
  cat <<EOF
AtomMove.TypeOfRun          static
IO.DumpChargeDensity        T
minE.SelfConsistent         T
minE.SCTolerance            1.0e-8
Diag.MPMesh                 T
Diag.GammaCentred           T
Diag.MPMeshX                $K_MESH
Diag.MPMeshY                $K_MESH
Diag.MPMeshZ                $K_MESH
Diag.SmearingType           1
Diag.MPOrder                1
Diag.kT                     0.003
EOF
} > "$SCF_DIR/Conquest_input"
run_conquest "$SCF_DIR"
grep -q "Reached SCF tolerance" "$SCF_DIR/Conquest_out"
grep -Eq "Number of electrons[[:space:]]*=[[:space:]]*96\\.0" \
  "$SCF_DIR/Conquest_out"

echo "[2/4] Fixed-density l-resolved projected DOS"
stage_species "$PDOS_DIR"
cp "$SCF_DIR/coords.dat" "$PDOS_DIR/coords.dat"
cp "$SCF_DIR"/chden.* "$PDOS_DIR/"
{
  echo "IO.Title monoclinic_hfo2_pdos"
  common_input
  cat <<EOF
AtomMove.TypeOfRun          static
minE.SelfConsistent         F
General.LoadRho             T
IO.writeDOS                 T
IO.write_proj_DOS           T
Diag.MPMesh                 T
Diag.GammaCentred           T
Diag.MPMeshX                $K_MESH
Diag.MPMeshY                $K_MESH
Diag.MPMeshZ                $K_MESH
EOF
} > "$PDOS_DIR/Conquest_input"
run_conquest "$PDOS_DIR"
cat >> "$PDOS_DIR/Conquest_input" <<'EOF'
Process.Job                  pdos
Process.n_DOS               3001
Process.sigma_DOS           0.008
Process.WFRangeRelative     T
Process.min_DOS_E           -1.50
Process.max_DOS_E            1.00
Process.pDOS_l_resolved     T
EOF
run_postprocess "$PDOS_DIR"
[[ -s "$PDOS_DIR/DOS.dat" ]]
[[ "$(find "$PDOS_DIR" -maxdepth 1 -name 'Atom*DOS_l.dat' | wc -l)" -eq 12 ]]

echo "[3/4] HPKOT/SeeK-path fixed-density band structure"
"$PYTHON" "$SCRIPT_DIR/generate_seekpath.py" "$SCF_DIR/coords.dat" \
  --output "$RESULTS_DIR/seekpath.json" \
  --conquest-block "$RESULTS_DIR/kpoint_block.dat" \
  > "$RESULTS_DIR/seekpath.log"
grep -q '"spacegroup_number": 14' "$RESULTS_DIR/seekpath.json"
stage_species "$BAND_DIR"
cp "$SCF_DIR/coords.dat" "$BAND_DIR/coords.dat"
cp "$SCF_DIR"/chden.* "$BAND_DIR/"
{
  echo "IO.Title monoclinic_hfo2_hpkot_bands"
  common_input
  cat <<EOF
AtomMove.TypeOfRun          static
minE.SelfConsistent         F
General.LoadRho             T
Diag.KspaceLines            T
Diag.NumKpts                $BAND_POINTS
EOF
  cat "$RESULTS_DIR/kpoint_block.dat"
} > "$BAND_DIR/Conquest_input"
run_conquest "$BAND_DIR"
[[ -s "$BAND_DIR/eigenvalues.dat" ]]

echo "[4/4] Zero-width-branch band/pDOS plot and physics summary"
MPLCONFIGDIR="$RESULTS_DIR/.matplotlib" "$PYTHON" \
  "$SCRIPT_DIR/plot_hfo2_band_pdos.py" \
  --bands "$BAND_DIR/eigenvalues.dat" \
  --dos "$PDOS_DIR/DOS.dat" \
  --pdos-dir "$PDOS_DIR" \
  --coords "$BAND_DIR/coords.dat" \
  --seekpath "$RESULTS_DIR/seekpath.json" \
  --points-per-segment "$BAND_POINTS" \
  --output "$RESULTS_DIR/monoclinic_hfo2_band_pdos.png" \
  --summary "$RESULTS_DIR/summary.json"

echo "PASS: monoclinic HfO2 SCF, pDOS, and HPKOT bands completed."
