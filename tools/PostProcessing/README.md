Note to developers:

The Conquest files in this directory are essentially all taken from
../../src with a few changes.

1. io_module.f90 has most routines removed (keeping
read_atomic_positions, write_eigenvalues, banner, get_file_name and
get_file_name_2rank)
2. pseudo_tm_info.f90 has lines referencing modules XC and
sfc_partitions and associated variables (gap_threshold and
functional_*) removed

berry_module.f90 is specific to PostProcessCQ (no counterpart in
../../src): Berry-phase polarisation (Process.Job pol), polarisation
changes and mode effective charges (dpo) and finite-difference Born
effective charges (bec).  make_bec_displacements.py creates the
displaced run directories for bec.  See docs/post-proc.rst.
