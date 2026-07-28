#!/bin/sh
set -eu

case_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "${case_dir}/../.." && pwd)
run_dir="${case_dir}/ewald_cell_smoke"
conquest_bin=${CONQUEST_BIN:-"${repo_dir}/bin/Conquest"}
mpi_ranks=${MPI_RANKS:-2}
output_file="${run_dir}/Conquest_out"

case "${mpi_ranks}" in
  ''|*[!0-9]*)
    echo "MPI_RANKS must be a positive integer" >&2
    exit 2
    ;;
esac
if [ "${mpi_ranks}" -lt 1 ] || [ "${mpi_ranks}" -gt 4 ]; then
  echo "This 12-atom test permits one to four MPI ranks" >&2
  exit 2
fi
if [ ! -x "${conquest_bin}" ]; then
  echo "CONQUEST executable not found: ${conquest_bin}" >&2
  exit 2
fi

cp "${case_dir}/HfCQ.ion" "${run_dir}/HfCQ.ion"
cp "${case_dir}/OCQ.ion" "${run_dir}/OCQ.ion"
rm -f "${output_file}" "${run_dir}/Conquest_warnings"

(
  cd "${run_dir}"
  mpirun -np "${mpi_ranks}" "${conquest_bin}" > "${output_file}"
)

if grep -q "You must use neutral atom for cell optimisation" "${output_file}"; then
  echo "FAIL: explicit Ewald cell optimisation was rejected" >&2
  exit 1
fi
if ! grep -q "Ewald total energy" "${output_file}"; then
  echo "FAIL: no Ewald energy was evaluated" >&2
  exit 1
fi
if ! grep -q "full_double_loop: ionic relaxation" "${output_file}"; then
  echo "FAIL: coupled atom/cell method 2 did not enter ionic relaxation" >&2
  exit 1
fi
if ! grep -q "set_ewald: Ewald" "${output_file}"; then
  echo "FAIL: Ewald state was not reported" >&2
  exit 1
fi
if grep -q "No resolvable downhill full-lattice step" "${output_file}"; then
  echo "FAIL: full-lattice line search did not find a downhill step" >&2
  exit 1
fi

set_ewald_calls=$(grep -c "set_ewald: Ewald" "${output_file}")
if [ "${set_ewald_calls}" -lt 2 ]; then
  echo "FAIL: Ewald state was not rebuilt after a lattice trial" >&2
  exit 1
fi
accepted_cell_steps=$(grep -c "back_lm_lattice: exit after" "${output_file}")
if [ "${accepted_cell_steps}" -lt 1 ]; then
  echo "FAIL: no full-lattice line-search step was accepted" >&2
  exit 1
fi
converged_cell_cycles=$(grep -c \
  "cell_cg_run:Maximum stress below threshold" "${output_file}")
if [ "${converged_cell_cycles}" -lt 1 ]; then
  echo "FAIL: no coupled cell cycle reached the stress threshold" >&2
  exit 1
fi

echo "PASS: coupled monoclinic HfO2 accepted ${accepted_cell_steps} cell steps,"
echo "      converged ${converged_cell_cycles} cell cycles, and rebuilt Ewald"
echo "      state ${set_ewald_calls} times."
