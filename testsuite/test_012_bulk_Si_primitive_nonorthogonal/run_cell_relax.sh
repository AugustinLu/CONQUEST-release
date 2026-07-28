#!/usr/bin/env bash
# Full six-strain lattice relaxation of the arbitrarily oriented primitive Si cell.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONQUEST_BIN="${CONQUEST_BIN:-$RELEASE_DIR/bin/Conquest}"
MPI_LAUNCHER="${MPI_LAUNCHER:-mpirun}"
PYTHON="${PYTHON:-/opt/anaconda3/bin/python}"
NP="${NP:-2}"
BACKGROUND_MODE="${BACKGROUND_MODE:-auto}"
RUN_DIR="${RUN_DIR:-$SCRIPT_DIR/results/cell_relax}"

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
if [[ -e "$RUN_DIR" ]]; then
  archive="${RUN_DIR}.previous.$(date +%Y%m%d-%H%M%S)"
  mv "$RUN_DIR" "$archive"
  echo "Previous cell relaxation preserved in $archive"
fi
mkdir -p "$RUN_DIR"
cp "$SCRIPT_DIR/coords_ideal.dat" "$RUN_DIR/coords.dat"
cp "$SCRIPT_DIR/Si.ion" "$RUN_DIR/Si.ion"

cat > "$RUN_DIR/Conquest_input" <<'EOF'
IO.Title                     primitive_si_full_lattice_relax
IO.Coordinates               coords.dat
IO.FractionalAtomicCoords    T
IO.Iprint_MD                 3

AtomMove.TypeOfRun           cg
AtomMove.OptCell             T
AtomMove.OptCellMethod       1
AtomMove.OptCell.Constraint  none
AtomMove.FullStress          T
AtomMove.ReuseDM             T
AtomMove.CGLineMin           backtrack
AtomMove.NumSteps            20
AtomMove.EnthalpyTolerance   1.0e-7
AtomMove.StressTolerance     0.10

General.NumberOfSpecies      1
General.PAOFromFiles         T
%block ChemicalSpeciesLabel
1 28.086 Si Si.ion
%endblock

Grid.GridCutoff              80
DM.SolutionMethod            diagon
minE.SelfConsistent          T
minE.SCTolerance             1.0e-8
Diag.MPMesh                  T
Diag.GammaCentred            T
Diag.MPMeshX                 6
Diag.MPMeshY                 6
Diag.MPMeshZ                 6
EOF

echo "Primitive Si full-lattice relaxation"
echo "  MPI ranks       : $NP"
echo "  taskpolicy -b   : $BACKGROUND_MODE"
(
  cd "$RUN_DIR"
  if [[ "$BACKGROUND_MODE" == T ]]; then
    /usr/sbin/taskpolicy -b "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" \
      > mpi.log 2>&1
  else
    "$MPI_LAUNCHER" -np "$NP" "$CONQUEST_BIN" > mpi.log 2>&1
  fi
)

"$PYTHON" "$SCRIPT_DIR/analyze_cell_relax.py" \
  --initial "$RUN_DIR/coords.dat" \
  --final "$RUN_DIR/UpdatedAtoms.dat" \
  --output "$RUN_DIR/Conquest_out" \
  --summary "$RUN_DIR/summary.json"
