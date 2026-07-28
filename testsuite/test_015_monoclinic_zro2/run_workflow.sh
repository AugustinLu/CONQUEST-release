#!/usr/bin/env bash
# Monoclinic ZrO2: atomic relaxation -> SCF -> pDOS -> HPKOT bands -> plot.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
POSTPROCESS_BIN="${POSTPROCESS_BIN:-$RELEASE_DIR/bin/PostProcessCQ}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
NP="${NP:-2}"
BACKGROUND_MODE="${BACKGROUND_MODE:-F}"
RESULTS_DIR="${RESULTS_DIR:-$SCRIPT_DIR/results}"
BAND_POINTS="${BAND_POINTS:-25}"
RESUME_RELAX="${RESUME_RELAX:-F}"

if (( NP < 1 || NP > 4 )); then
  echo "ERROR: this 12-atom test permits one to four MPI ranks." >&2
  exit 2
fi
for executable in "$CONQUEST_BIN" "$POSTPROCESS_BIN" "$PYTHON"; do
  if [[ ! -x "$executable" ]]; then
    echo "ERROR: executable not found: $executable" >&2
    exit 2
  fi
done
if [[ "$BACKGROUND_MODE" == T && ! -x /usr/sbin/taskpolicy ]]; then
  echo "ERROR: taskpolicy requested but unavailable." >&2
  exit 2
fi
if [[ -e "$RESULTS_DIR" && "$RESUME_RELAX" != T ]]; then
  archive="${RESULTS_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RESULTS_DIR" "$archive"
  echo "Previous results preserved in $archive"
fi
RELAX_DIR="$RESULTS_DIR/relax"
SCF_DIR="$RESULTS_DIR/scf"
PDOS_DIR="$RESULTS_DIR/pdos"
BAND_DIR="$RESULTS_DIR/bands"
mkdir -p "$RELAX_DIR" "$SCF_DIR" "$PDOS_DIR" "$BAND_DIR" \
  "$RESULTS_DIR/.matplotlib"

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
  cp "$SCRIPT_DIR/Zr.ion" "$1/Zr.ion"
  cp "$SCRIPT_DIR/O.ion" "$1/O.ion"
}

common_input() {
  cat <<'EOF'
IO.Coordinates              coords.dat
IO.FractionalAtomicCoords   T
General.NumberOfSpecies     2
General.DifferentFunctional T
General.FunctionalType      101
General.PAOFromFiles        T
General.NeutralAtom         F
%block ChemicalSpeciesLabel
1 91.2240 Zr Zr.ion
2 15.9994 O  O.ion
%endblock
Basis.BasisSet              PAOs
Grid.GridCutoff             100
DM.SolutionMethod           diagon
EOF
}

echo "[1/5] Fixed-cell relaxation of all baddeleyite internal coordinates"
if [[ "$RESUME_RELAX" == T ]]; then
  [[ -s "$RELAX_DIR/coord_next.dat" && -s "$RELAX_DIR/Conquest_out" ]]
  echo "Reusing completed relaxation in $RELAX_DIR"
else
  stage_species "$RELAX_DIR"
  cp "$SCRIPT_DIR/coords_relax_start.dat" "$RELAX_DIR/coords.dat"
  {
    echo "IO.Title monoclinic_zro2_relax"
    common_input
    cat <<'EOF'
AtomMove.TypeOfRun          cg
AtomMove.OptCell            F
AtomMove.NumSteps           50
AtomMove.MaxForceTol        5.0e-4
AtomMove.ReuseDM            T
AtomMove.CGLineMin          backtrack
minE.SelfConsistent         T
minE.SCTolerance            1.0e-8
Diag.MPMesh                 T
Diag.GammaCentred           T
Diag.MPMeshX                3
Diag.MPMeshY                3
Diag.MPMeshZ                3
EOF
  } > "$RELAX_DIR/Conquest_input"
  run_conquest "$RELAX_DIR"
  [[ -s "$RELAX_DIR/coord_next.dat" ]]
fi

echo "[2/5] Symmetry restoration and converged SCF density"
stage_species "$SCF_DIR"
"$PYTHON" "$SCRIPT_DIR/symmetrize_baddeleyite.py" \
  "$RELAX_DIR/coord_next.dat" "$SCF_DIR/coords.dat" \
  > "$SCF_DIR/symmetrize.log"
{
  echo "IO.Title monoclinic_zro2_scf"
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
Diag.MPMeshZ                4
EOF
} > "$SCF_DIR/Conquest_input"
run_conquest "$SCF_DIR"
grep -q "Reached SCF tolerance" "$SCF_DIR/Conquest_out"
grep -Eq "Number of electrons[[:space:]]*=[[:space:]]*96\\.0" \
  "$SCF_DIR/Conquest_out"

echo "[3/5] Fixed-density l-resolved projected DOS"
stage_species "$PDOS_DIR"
cp "$SCF_DIR/coords.dat" "$PDOS_DIR/coords.dat"
cp "$SCF_DIR"/chden.* "$PDOS_DIR/"
{
  echo "IO.Title monoclinic_zro2_pdos"
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
Diag.MPMeshZ                5
EOF
} > "$PDOS_DIR/Conquest_input"
run_conquest "$PDOS_DIR"
cat >> "$PDOS_DIR/Conquest_input" <<'EOF'
Process.Job                  pdos
Process.n_DOS               3501
Process.sigma_DOS           0.008
Process.WFRangeRelative     T
Process.min_DOS_E           -1.50
Process.max_DOS_E            0.80
Process.pDOS_l_resolved     T
EOF
(
  cd "$PDOS_DIR"
  "$MPI_LAUNCHER" -np 1 "$POSTPROCESS_BIN" > PostProcess_pdos.log 2>&1
)
[[ -s "$PDOS_DIR/DOS.dat" ]]
[[ "$(find "$PDOS_DIR" -maxdepth 1 -name 'Atom*DOS_l.dat' | wc -l)" -eq 12 ]]

echo "[4/5] HPKOT/SeeK-path fixed-density band structure"
"$PYTHON" "$SCRIPT_DIR/generate_seekpath.py" "$SCF_DIR/coords.dat" \
  --output "$RESULTS_DIR/seekpath.json" \
  --conquest-block "$RESULTS_DIR/kpoint_block.dat" \
  > "$RESULTS_DIR/seekpath.log"
grep -q '"spacegroup_number": 14' "$RESULTS_DIR/seekpath.json"
stage_species "$BAND_DIR"
cp "$SCF_DIR/coords.dat" "$BAND_DIR/coords.dat"
cp "$SCF_DIR"/chden.* "$BAND_DIR/"
{
  echo "IO.Title monoclinic_zro2_hpkot_bands"
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

echo "[5/5] Zero-width-branch band/pDOS plot and summary"
MPLCONFIGDIR="$RESULTS_DIR/.matplotlib" "$PYTHON" \
  "$SCRIPT_DIR/plot_zro2_band_pdos.py" \
  --bands "$BAND_DIR/eigenvalues.dat" \
  --dos "$PDOS_DIR/DOS.dat" \
  --pdos-dir "$PDOS_DIR" \
  --coords "$BAND_DIR/coords.dat" \
  --seekpath "$RESULTS_DIR/seekpath.json" \
  --points-per-segment "$BAND_POINTS" \
  --relax-output "$RELAX_DIR/Conquest_out" \
  --output "$RESULTS_DIR/monoclinic_zro2_band_pdos.png" \
  --summary "$RESULTS_DIR/summary.json"

echo "PASS: monoclinic ZrO2 relaxation, SCF, pDOS, and HPKOT bands completed."
