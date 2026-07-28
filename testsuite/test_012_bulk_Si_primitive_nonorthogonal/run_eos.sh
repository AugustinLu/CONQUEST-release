#!/usr/bin/env bash
# Nine-point primitive-Si hydrostatic EOS and third-order Birch-Murnaghan fit.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
NP="${NP:-2}"
BACKGROUND_MODE="${BACKGROUND_MODE:-auto}"
EOS_ROOT="${EOS_ROOT:-$SCRIPT_DIR/results/eos}"
GRID_CUTOFF="${GRID_CUTOFF:-80}"
K_MESH="${K_MESH:-6}"

if [[ "$BACKGROUND_MODE" == auto ]]; then
  if [[ "$(uname -s)" == Darwin && -x /usr/sbin/taskpolicy ]]; then
    BACKGROUND_MODE=T
  else
    BACKGROUND_MODE=F
  fi
fi
if (( NP < 1 || NP > 2 )); then
  echo "ERROR: primitive Si has two atoms; NP must be 1 or 2." >&2
  exit 2
fi

if [[ -e "$EOS_ROOT" ]]; then
  archive="${EOS_ROOT}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$EOS_ROOT" "$archive"
  echo "Previous EOS preserved in $archive"
fi
mkdir -p "$EOS_ROOT/.matplotlib"
"$PYTHON" "$SCRIPT_DIR/eos_birch_murnaghan.py" prepare \
  --base "$SCRIPT_DIR/coords_ideal.dat" --root "$EOS_ROOT" \
  > "$EOS_ROOT/prepare.log"

run_point() {
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
  grep -q "Reached SCF tolerance" "$directory/Conquest_out"
}

echo "Primitive Si Birch-Murnaghan EOS"
echo "  MPI ranks       : $NP"
echo "  taskpolicy -b   : $BACKGROUND_MODE"

for directory in "$EOS_ROOT"/volume_*; do
  cp "$SCRIPT_DIR/Si.ion" "$directory/Si.ion"
  cat > "$directory/Conquest_input" <<EOF
IO.Title                    primitive_si_eos
IO.Coordinates              coords.dat
IO.FractionalAtomicCoords   T
AtomMove.TypeOfRun          static
General.NumberOfSpecies     1
General.PAOFromFiles        T
%block ChemicalSpeciesLabel
1 28.086 Si Si.ion
%endblock
Grid.GridCutoff             $GRID_CUTOFF
DM.SolutionMethod           diagon
minE.SelfConsistent         T
minE.SCTolerance            1.0e-8
Diag.MPMesh                 T
Diag.GammaCentred           T
Diag.MPMeshX                $K_MESH
Diag.MPMeshY                $K_MESH
Diag.MPMeshZ                $K_MESH
EOF
  echo "Running $(basename "$directory")"
  run_point "$directory"
done

MPLCONFIGDIR="$EOS_ROOT/.matplotlib" "$PYTHON" \
  "$SCRIPT_DIR/eos_birch_murnaghan.py" fit \
  --root "$EOS_ROOT" \
  --image "$EOS_ROOT/primitive_si_birch_murnaghan.png" \
  --summary "$EOS_ROOT/summary.json"
