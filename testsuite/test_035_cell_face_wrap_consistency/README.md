# Test 035: atoms on a cell face are wrapped consistently with the partitions

This regression runs the same 16-atom nonorthogonal silicon supercell twice.
The two coordinate files differ only in the atoms that sit on a cell face:
their zero fractional coordinates are written as `-1.0e-12` in
`coords_below_face.dat` and as `+1.0e-12` in `coords_above_face.dat`.  Both are
well inside the `shift_in_bohr` boundary tolerance, so the two inputs describe
the same structure and must give the same energy, forces and stress.

It guards the read-time wrap in `wrap_into_cell`.  That routine used
`f - floor(f)` while the partitioners used `f - floor(f + eps_frac)`.  A
coordinate a hair below a face (which also arises when an exact `0.0` is
converted to Cartesian and back in a skewed cell) was then stored one lattice
vector away from the partition it was assigned to, the covering sets missed
some of its neighbours, and the run either aborted with
`index_trans: i_h2d wrong` or completed with wrong results.

`General.NPartitionsX/Y/Z 2` is set deliberately.  The fault needs more than
one partition along the affected lattice direction, which the automatic
partitioner only produces at higher MPI rank counts; fixing the partition
count makes the test sensitive at one to four ranks.  One interior atom is
displaced so that the compared forces are not zero by symmetry.

Run with:

```bash
./run_workflow.sh
```

`NP` selects the number of MPI ranks (default 2, at most 4).
`check_face_wrap.py` requires the two total energies to agree within
`1e-7 Ha`, the maximum force and force residual within `1e-6 Ha/a0`, and the
first row of the stress tensor within `1e-4 GPa`.
