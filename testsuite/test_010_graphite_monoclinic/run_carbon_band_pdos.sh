#!/usr/bin/env bash
# Reproducible CONQUEST SCF -> fixed-density pDOS -> band-structure workflow.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
MATERIAL="${1:-}"

case "$MATERIAL" in
  graphite)
    COORDS_SOURCE="$SCRIPT_DIR/structures/graphite_ab_literature.coords"
    SCF_KX="${SCF_KX:-15}"
    SCF_KY="${SCF_KY:-15}"
    SCF_KZ="${SCF_KZ:-5}"
    BAND_SEGMENTS=4
    BAND_POINTS="${BAND_POINTS:-50}"
    OCCUPIED_BANDS=8
    PATH_NAME="Gamma-M-K-Gamma-A"
    BAND_PATH=$'0.0      0.0      0.0\n0.5      0.0      0.0\n0.5      0.0      0.0\n0.333333 0.333333 0.0\n0.333333 0.333333 0.0\n0.0      0.0      0.0\n0.0      0.0      0.0\n0.0      0.0      0.5'
    ;;
  graphene)
    COORDS_SOURCE="$SCRIPT_DIR/structures/graphene_literature.coords"
    SCF_KX="${SCF_KX:-21}"
    SCF_KY="${SCF_KY:-21}"
    SCF_KZ=1
    BAND_SEGMENTS=3
    BAND_POINTS="${BAND_POINTS:-60}"
    OCCUPIED_BANDS=4
    PATH_NAME="Gamma-M-K-Gamma"
    BAND_PATH=$'0.0      0.0      0.0\n0.5      0.0      0.0\n0.5      0.0      0.0\n0.333333 0.333333 0.0\n0.333333 0.333333 0.0\n0.0      0.0      0.0'
    ;;
  *)
    echo "Usage: $0 graphite|graphene" >&2
    exit 2
    ;;
esac

CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
POSTPROCESS_BIN="${POSTPROCESS_BIN:-$RELEASE_DIR/bin/PostProcessCQ}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
NP="${NP:-2}"
GRID_CUTOFF="${GRID_CUTOFF:-120}"
SCF_TOLERANCE="${SCF_TOLERANCE:-1.0e-8}"
PDOS_POINTS="${PDOS_POINTS:-2001}"
PDOS_SIGMA="${PDOS_SIGMA:-0.01}"
PDOS_EMIN="${PDOS_EMIN:--0.8}"
PDOS_EMAX="${PDOS_EMAX:-0.6}"
ION_FILE="${ION_FILE:-$SCRIPT_DIR/C_PBE_SZP_CQ.ion}"
RESULTS_ROOT="${RESULTS_ROOT:-$SCRIPT_DIR/band_pdos_results}"
RUN_DIR="${RUN_DIR:-$RESULTS_ROOT/$MATERIAL}"
SCF_DIR="$RUN_DIR/scf"
PDOS_DIR="$RUN_DIR/pdos"
BAND_DIR="$RUN_DIR/bands"

if [[ "$NP" != 1 && "$NP" != 2 ]]; then
  echo "ERROR: NP must be 1 or 2 (the project limit is two MPI ranks)." >&2
  exit 2
fi
for executable in "$CONQUEST_BIN" "$POSTPROCESS_BIN"; do
  if [[ ! -x "$executable" ]]; then
    echo "ERROR: executable not found: $executable" >&2
    exit 1
  fi
done
if ! command -v "$MPI_LAUNCHER" >/dev/null 2>&1; then
  echo "ERROR: MPI launcher not found: $MPI_LAUNCHER" >&2
  exit 1
fi
for input_file in "$COORDS_SOURCE" "$ION_FILE" "$SCRIPT_DIR/plot_band_pdos.js"; do
  if [[ ! -f "$input_file" ]]; then
    echo "ERROR: required file not found: $input_file" >&2
    exit 1
  fi
done

# Preserve an earlier run rather than deleting it.
if [[ -e "$RUN_DIR" ]]; then
  archive="${RUN_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RUN_DIR" "$archive"
  echo "Previous results preserved in $archive"
fi
mkdir -p "$SCF_DIR" "$PDOS_DIR" "$BAND_DIR"

write_common_input() {
  cat <<EOF
IO.Coordinates              coords.dat
IO.FractionalAtomicCoords   T
AtomMove.TypeOfRun          static

General.NumberOfSpecies     1
General.DifferentFunctional T
General.FunctionalType      101
General.PAOFromFiles        T
%block ChemicalSpeciesLabel
1 12.011 C C.ion
%endblock

Grid.GridCutoff             $GRID_CUTOFF
DM.SolutionMethod           diagon
EOF
}

stage_inputs() {
  local destination="$1"
  cp "$COORDS_SOURCE" "$destination/coords.dat"
  cp "$ION_FILE" "$destination/C.ion"
}

run_conquest() {
  local directory="$1"
  (
    cd "$directory"
    "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" > mpi.log 2>&1
  )
  if [[ ! -s "$directory/Conquest_out" ]]; then
    echo "ERROR: CONQUEST failed in $directory; see mpi.log" >&2
    exit 1
  fi
}

echo "============================================================"
echo " CONQUEST $MATERIAL band structure + pDOS"
echo " cell       : $COORDS_SOURCE"
echo " MPI ranks  : $NP"
echo " SCF mesh   : ${SCF_KX}x${SCF_KY}x${SCF_KZ}"
echo " results    : $RUN_DIR"
echo "============================================================"

echo "[1/4] Self-consistent density"
stage_inputs "$SCF_DIR"
{
  echo "IO.Title                    ${MATERIAL}_scf"
  write_common_input
  cat <<EOF
IO.DumpChargeDensity        T
minE.SelfConsistent         T
minE.SCTolerance            $SCF_TOLERANCE
Diag.MPMesh                 T
Diag.MPMeshX                $SCF_KX
Diag.MPMeshY                $SCF_KY
Diag.MPMeshZ                $SCF_KZ
EOF
} > "$SCF_DIR/Conquest_input"
run_conquest "$SCF_DIR"
if ! grep -q "Reached SCF tolerance" "$SCF_DIR/Conquest_out"; then
  echo "ERROR: SCF did not converge; see $SCF_DIR/Conquest_out" >&2
  exit 1
fi
if ! compgen -G "$SCF_DIR/chden.*" >/dev/null; then
  echo "ERROR: SCF did not write chden.*" >&2
  exit 1
fi

echo "[2/4] Fixed-density wavefunctions and l-resolved pDOS"
stage_inputs "$PDOS_DIR"
cp "$SCF_DIR"/chden.* "$PDOS_DIR/"
{
  echo "IO.Title                    ${MATERIAL}_pdos"
  write_common_input
  cat <<EOF
minE.SelfConsistent         F
General.LoadRho             T
IO.writeDOS                 T
IO.write_proj_DOS           T
Diag.MPMesh                 T
Diag.MPMeshX                $SCF_KX
Diag.MPMeshY                $SCF_KY
Diag.MPMeshZ                $SCF_KZ
EOF
} > "$PDOS_DIR/Conquest_input"
run_conquest "$PDOS_DIR"
if [[ ! -s "$PDOS_DIR/eigenvalues.dat" ]] || ! compgen -G "$PDOS_DIR/Process[0-9]*WF.dat" >/dev/null; then
  echo "ERROR: fixed-density pDOS export is incomplete in $PDOS_DIR" >&2
  exit 1
fi
cat >> "$PDOS_DIR/Conquest_input" <<EOF

Process.Job                 pdos
Process.n_DOS               $PDOS_POINTS
Process.sigma_DOS           $PDOS_SIGMA
Process.WFRangeRelative     T
Process.min_DOS_E           $PDOS_EMIN
Process.max_DOS_E           $PDOS_EMAX
Process.pDOS_l_resolved     T
EOF
(
  cd "$PDOS_DIR"
  "$MPI_LAUNCHER" -np 1 "$POSTPROCESS_BIN" > PostProcess_pdos.log 2>&1
)
EXPECTED_ATOMS="$(awk 'NR == 4 { print $1 }' "$PDOS_DIR/coords.dat")"
FOUND_ATOMS="$(find "$PDOS_DIR" -maxdepth 1 -name 'Atom*DOS_l.dat' -type f | wc -l | tr -d ' ')"
if [[ ! -s "$PDOS_DIR/DOS.dat" || "$FOUND_ATOMS" != "$EXPECTED_ATOMS" ]]; then
  echo "ERROR: expected $EXPECTED_ATOMS atom pDOS files, found $FOUND_ATOMS; see $PDOS_DIR/PostProcess_pdos.log" >&2
  exit 1
fi

echo "[3/4] Band path $PATH_NAME"
stage_inputs "$BAND_DIR"
cp "$SCF_DIR"/chden.* "$BAND_DIR/"
{
  echo "IO.Title                    ${MATERIAL}_bands"
  write_common_input
  cat <<EOF
minE.SelfConsistent         F
General.LoadRho             T
Diag.KspaceLines            T
Diag.NumKptLines            $BAND_SEGMENTS
Diag.NumKpts                $BAND_POINTS
%block Diag.KpointLines
$BAND_PATH
%endblock
EOF
} > "$BAND_DIR/Conquest_input"
run_conquest "$BAND_DIR"
EXPECTED_KPOINTS=$((BAND_SEGMENTS * (BAND_POINTS - 1) + 1))
FOUND_KPOINTS="$(awk 'NR == 1 { print $4 }' "$BAND_DIR/eigenvalues.dat")"
if [[ "$FOUND_KPOINTS" != "$EXPECTED_KPOINTS" ]]; then
  echo "ERROR: expected $EXPECTED_KPOINTS band k-points, found $FOUND_KPOINTS" >&2
  exit 1
fi

echo "[4/4] Combined band + pDOS image"
if [[ -n "${NODE_BIN:-}" ]]; then
  node_executable="$NODE_BIN"
elif command -v node >/dev/null 2>&1; then
  node_executable="$(command -v node)"
else
  CODEX_RUNTIME_SEARCH="${CODEX_RUNTIME_SEARCH:-${HOME}/.cache/codex-runtimes}"
  node_executable="$(find "$CODEX_RUNTIME_SEARCH" -path '*/dependencies/node/bin/node' -type f -perm -u+x -print -quit 2>/dev/null || true)"
  if [[ -z "$node_executable" ]]; then
    echo "ERROR: Node.js is required for plotting; set NODE_BIN=/path/to/node" >&2
    exit 1
  fi
fi
node_root="$(cd -- "$(dirname -- "$node_executable")/.." && pwd)"
if [[ -d "$node_root/node_modules/sharp" ]]; then
  if [[ -n "${NODE_PATH:-}" ]]; then
    export NODE_PATH="$NODE_PATH:$node_root/node_modules"
  else
    export NODE_PATH="$node_root/node_modules"
  fi
fi
"$node_executable" "$SCRIPT_DIR/plot_band_pdos.js" \
  "$MATERIAL" "$BAND_DIR/eigenvalues.dat" "$PDOS_DIR/DOS.dat" "$PDOS_DIR" \
  "$RUN_DIR/${MATERIAL}_band_pdos" "$BAND_POINTS" "$BAND_SEGMENTS" "$OCCUPIED_BANDS"

if [[ ! -s "$RUN_DIR/${MATERIAL}_band_pdos.svg" ]]; then
  echo "ERROR: plot was not written" >&2
  exit 1
fi

echo
echo "Done: $RUN_DIR"
echo "  bands : $BAND_DIR/eigenvalues.dat"
echo "  pDOS  : $PDOS_DIR/DOS.dat and Atom*DOS_l.dat"
echo "  image : $RUN_DIR/${MATERIAL}_band_pdos.svg"
if [[ -s "$RUN_DIR/${MATERIAL}_band_pdos.png" ]]; then
  echo "          $RUN_DIR/${MATERIAL}_band_pdos.png"
fi
