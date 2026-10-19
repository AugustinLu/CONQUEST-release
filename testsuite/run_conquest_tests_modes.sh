#!/bin/bash

# Linux/macOS version of run_conquest_tests_windows.sh.
#
# Runs every test_[0-9][0-9][0-9]_* directory with mpirun for each "NPxNT"
# mode given on the command line (NP = MPI processes, NT = OpenMP threads),
# then checks the results with pytest.  Outputs are kept in
# $OUTROOT/<mode>/ so that modes and builds can be compared.
#
# Usage (in this directory):
#   ./run_conquest_tests_modes.sh                  # 1x1 4x1 1x4 2x2
#   ./run_conquest_tests_modes.sh 16x1 64x1        # custom modes
#
# Environment:
#   CONQUEST      executable (default ../bin/Conquest)
#   MPIRUN        launcher (default mpirun)
#   MPIRUN_OPTS   extra launcher options, e.g. "--oversubscribe"
#   OUTROOT       output directory (default results_<short hostname>)
#   CONQUEST_USE_CUDA, CONQUEST_CUDA_MIN_N, ... are passed through, e.g. to
#   force every GPU path:
#     CONQUEST_CUDA_MIN_N=1 CONQUEST_CUDA_MIN_FFT=1 CONQUEST_CUDA_MIN_FLOPS=1e5 \
#     CONQUEST_CUDA_IN_PARALLEL=1 OUTROOT=results_gpu_forced ./run_conquest_tests_modes.sh

MODES=${*:-"1x1 4x1 1x4 2x2"}

CONQUEST=${CONQUEST:-$(cd ../bin && pwd)/Conquest}
MPIRUN=${MPIRUN:-mpirun}
OUTROOT=${OUTROOT:-results_$(hostname -s)}
export OMP_STACKSIZE=100M
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

if [ ! -x "$CONQUEST" ]; then
    echo "Cannot find $CONQUEST - build it first with: (cd ../src; make)"
    exit 1
fi

mkdir -p "$OUTROOT"
{
    echo "date: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "host: $(hostname)"
    echo "executable: $CONQUEST"
    echo "launcher: $MPIRUN $MPIRUN_OPTS"
    env | grep '^CONQUEST_' | sort
} > "$OUTROOT/run_info.txt"

summary=""
for mode in $MODES
do
    NP=${mode%x*}
    NT=${mode#*x}
    export OMP_NUM_THREADS=$NT
    out=$OUTROOT/$mode
    mkdir -p "$out"
    echo "=== Mode $mode: $NP MPI processes x $NT OpenMP threads ==="
    for dn in test_[0-9][0-9][0-9]_*
    do
        [ -d "$dn" ] || continue
        # Conquest needs at least one atom per MPI process, so cap the
        # number of processes at the atom count (line 4 of the coordinates)
        coords=$(awk 'tolower($1)=="io.coordinates" {print $2}' "$dn/Conquest_input")
        natoms=$(sed -n 4p "$dn/$coords" | awk '{print $1}')
        np=$NP
        note=""
        if [ -n "$natoms" ] && [ "$natoms" -lt "$NP" ]; then
            np=$natoms
            note=" (capped at $np processes: only $natoms atoms)"
        fi
        start=$(date +%s)
        (cd "$dn"; rm -f Conquest_out; $MPIRUN $MPIRUN_OPTS -np "$np" "$CONQUEST" > stdout.log 2>&1)
        rc=$?
        echo "  $dn: exit $rc, $(( $(date +%s) - start )) s$note"
        cp "$dn/Conquest_out" "$out/$dn.Conquest_out" 2>/dev/null
        mv "$dn/stdout.log" "$out/$dn.stdout.log"
    done
    python3 -m pytest -q test_check_output.py > "$out/pytest.log" 2>&1
    result=$(tail -1 "$out/pytest.log")
    echo "  pytest: $result"
    summary="$summary\n  $mode: $result"
done

echo -e "\n=== Summary ===$summary"
