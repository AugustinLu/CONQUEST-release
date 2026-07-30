#!/usr/bin/env bash
# Validate published 3R graphite SFC/MPI behaviour and electronic structure.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
POSTPROCESS_BIN="${POSTPROCESS_BIN:-$RELEASE_DIR/bin/PostProcessCQ}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
BACKGROUND_MODE="${BACKGROUND_MODE:-F}"
RESULTS_DIR="${RESULTS_DIR:-$SCRIPT_DIR/results}"
ELECTRONIC_MESH="${ELECTRONIC_MESH:-8}"
BAND_POINTS="${BAND_POINTS:-35}"
PDOS_POINTS="${PDOS_POINTS:-3001}"
PDOS_SIGMA="${PDOS_SIGMA:-0.005}"
CARBON_ION="$RELEASE_DIR/testsuite/test_010_graphite_monoclinic/C_PBE_SZP_CQ.ion"

for executable in "$CONQUEST_BIN" "$POSTPROCESS_BIN" "$PYTHON"; do
  if [[ ! -x "$executable" ]]; then
    echo "ERROR: executable not found: $executable" >&2
    exit 1
  fi
done
if [[ ! -f "$CARBON_ION" ]]; then
  echo "ERROR: carbon ion file not found: $CARBON_ION" >&2
  exit 1
fi
if ! command -v "$MPI_LAUNCHER" >/dev/null 2>&1; then
  echo "ERROR: MPI launcher not found: $MPI_LAUNCHER" >&2
  exit 1
fi
if [[ "$BACKGROUND_MODE" == T && ! -x /usr/sbin/taskpolicy ]]; then
  echo "ERROR: taskpolicy requested but unavailable." >&2
  exit 1
fi
if [[ -e "$RESULTS_DIR" ]]; then
  archive="${RESULTS_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RESULTS_DIR" "$archive"
  echo "Previous results preserved in $archive"
fi
mkdir -p "$RESULTS_DIR"

run_conquest() {
  local directory="$1"
  local ranks="$2"
  (
    cd "$directory"
    if [[ "$BACKGROUND_MODE" == T ]]; then
      /usr/sbin/taskpolicy -b "$MPI_LAUNCHER" -np "$ranks" \
        "$CONQUEST_BIN" > mpi.log 2>&1
    else
      "$MPI_LAUNCHER" -np "$ranks" "$CONQUEST_BIN" > mpi.log 2>&1
    fi
  )
  if [[ ! -s "$directory/Conquest_out" ]]; then
    echo "ERROR: CONQUEST did not produce output in $directory" >&2
    exit 1
  fi
}

write_electronic_common_input() {
  cat <<EOF
IO.Coordinates              coords.dat
IO.FractionalAtomicCoords   T
General.NumberOfSpecies     1
General.PAOFromFiles        T
General.NeutralAtom         F
%block ChemicalSpeciesLabel
1 12.011 C C.ion
%endblock
Grid.GridCutoff             60
DM.SolutionMethod           diagon
EOF
}

stage_electronic_inputs() {
  local directory="$1"
  cp "$RESULTS_DIR/rhombohedral_np2/coords.dat" "$directory/coords.dat"
  cp "$CARBON_ION" "$directory/C.ion"
}

"$PYTHON" "$SCRIPT_DIR/rhombohedral_graphite.py" prepare --root "$RESULTS_DIR"

for representation in rhombohedral hexagonal; do
  for ranks in 1 2; do
    directory="$RESULTS_DIR/${representation}_np${ranks}"
    cp "$CARBON_ION" "$directory/C_PBE_SZP_CQ.ion"
    cp "$SCRIPT_DIR/static.Conquest_input" "$directory/Conquest_input"
    echo "Running $representation 3R graphite on $ranks MPI rank(s)"
    run_conquest "$directory" "$ranks"
  done
done

SCF_DIR="$RESULTS_DIR/electronic_scf"
PDOS_DIR="$RESULTS_DIR/pdos"
BAND_DIR="$RESULTS_DIR/bands"
mkdir -p "$SCF_DIR" "$PDOS_DIR" "$BAND_DIR" "$RESULTS_DIR/.matplotlib"

echo "Running denser primitive-cell SCF for bands and pDOS"
stage_electronic_inputs "$SCF_DIR"
{
  echo "IO.Title                    rhombohedral_graphite_electronic_scf"
  write_electronic_common_input
  cat <<EOF
AtomMove.TypeOfRun          static
IO.DumpChargeDensity        T
minE.SelfConsistent         T
minE.SCTolerance            1.0e-7
Diag.MPMesh                 T
Diag.GammaCentred           T
Diag.MPMeshX                $ELECTRONIC_MESH
Diag.MPMeshY                $ELECTRONIC_MESH
Diag.MPMeshZ                $ELECTRONIC_MESH
EOF
} > "$SCF_DIR/Conquest_input"
run_conquest "$SCF_DIR" 2
if ! grep -q "Reached SCF tolerance" "$SCF_DIR/Conquest_out"; then
  echo "ERROR: electronic-structure SCF did not converge" >&2
  exit 1
fi
if ! compgen -G "$SCF_DIR/chden.*" >/dev/null; then
  echo "ERROR: electronic-structure SCF did not write chden.*" >&2
  exit 1
fi

echo "Running fixed-density carbon-resolved pDOS"
stage_electronic_inputs "$PDOS_DIR"
cp "$SCF_DIR"/chden.* "$PDOS_DIR/"
{
  echo "IO.Title                    rhombohedral_graphite_pdos"
  write_electronic_common_input
  cat <<EOF
AtomMove.TypeOfRun          static
minE.SelfConsistent         F
General.LoadRho             T
IO.writeDOS                 T
IO.write_proj_DOS           T
Diag.MPMesh                 T
Diag.GammaCentred           T
Diag.MPMeshX                $ELECTRONIC_MESH
Diag.MPMeshY                $ELECTRONIC_MESH
Diag.MPMeshZ                $ELECTRONIC_MESH
EOF
} > "$PDOS_DIR/Conquest_input"
run_conquest "$PDOS_DIR" 2
cat >> "$PDOS_DIR/Conquest_input" <<EOF

Process.Job                 pdos
Process.n_DOS               $PDOS_POINTS
Process.sigma_DOS           $PDOS_SIGMA
Process.WFRangeRelative     T
Process.min_DOS_E           -0.90
Process.max_DOS_E            0.60
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

echo "Running fixed-density HPKOT/SeeK-path bands"
stage_electronic_inputs "$BAND_DIR"
cp "$SCF_DIR"/chden.* "$BAND_DIR/"
BAND_SEGMENTS="$("$PYTHON" -c \
  'import json,sys; print(len(json.load(open(sys.argv[1]))["path"]))' \
  "$RESULTS_DIR/seekpath.json")"
{
  echo "IO.Title                    rhombohedral_graphite_hpkot_bands"
  write_electronic_common_input
  cat <<EOF
AtomMove.TypeOfRun          static
minE.SelfConsistent         F
General.LoadRho             T
Diag.KspaceLines            T
Diag.NumKptLines            $BAND_SEGMENTS
Diag.NumKpts                $BAND_POINTS
%block Diag.KpointLines
EOF
  cat "$RESULTS_DIR/band_path.dat"
  echo "%endblock"
} > "$BAND_DIR/Conquest_input"
run_conquest "$BAND_DIR" 2
if [[ ! -s "$BAND_DIR/eigenvalues.dat" ]]; then
  echo "ERROR: band calculation did not write eigenvalues.dat" >&2
  exit 1
fi

echo "Plotting and validating 3R-graphite bands and pDOS"
MPLCONFIGDIR="$RESULTS_DIR/.matplotlib" "$PYTHON" \
  "$SCRIPT_DIR/plot_graphite_band_pdos.py" \
  --bands "$BAND_DIR/eigenvalues.dat" \
  --dos "$PDOS_DIR/DOS.dat" \
  --pdos-dir "$PDOS_DIR" \
  --coords "$BAND_DIR/coords.dat" \
  --seekpath "$RESULTS_DIR/seekpath.json" \
  --points-per-segment "$BAND_POINTS" \
  --gaussian-width-ha "$PDOS_SIGMA" \
  --output "$RESULTS_DIR/rhombohedral_graphite_band_pdos.png" \
  --summary "$RESULTS_DIR/band_summary.json"

"$PYTHON" "$SCRIPT_DIR/rhombohedral_graphite.py" analyse \
  --root "$RESULTS_DIR"
