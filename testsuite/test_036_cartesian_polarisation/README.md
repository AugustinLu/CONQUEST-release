# Cartesian polarization and rotations

Run `python3 check_rotation.py --results /tmp/polarisation-new-run` after
building CONQUEST. The results directory must be new. MPI uses one rank and
one thread; launch failures and unconverged SCF calculations are errors.

The test rotates a displaced silicon cell by 45 degrees and compares the
printed Cartesian vector after aligning integer polarization branches. It
also checks the reconstruction from reduced lattice coefficients and all
three single-direction modes: those report a vector contribution and quantum,
but cannot claim to have computed the complete Cartesian vector.

The scalar totals are retained for existing readers. They are signed lattice
contribution magnitudes, not Cartesian components or directional projections.
The vector is P = A p / V, defined modulo integer columns of A/V.
The existing test 017 additionally checks its change under an integer basis
transformation, modulo the quantum vectors.
