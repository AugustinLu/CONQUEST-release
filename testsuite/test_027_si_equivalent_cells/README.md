# Equivalent primitive and conventional diamond-Si cells

This regression compares static PBE total energies for the same diamond-Si
crystal represented by:

- the conventional cubic eight-atom cell; and
- the nonorthogonal FCC primitive two-atom cell.

It was added after a reported discrepancy was traced to placing the second
primitive-cell atom at fractional `(1/2,1/2,1/2)`.  For the primitive vectors
used here, the diamond basis displacement is fractional `(1/4,1/4,1/4)`.
The former coordinates instead generate a simple-cubic atomic lattice and a
closed-gap electronic structure.

The comparison uses a 400 Ha integration-grid cutoff and one MPI rank.  The
primitive cell uses a 19x19x19 gamma-centred k mesh.  Its reciprocal basis
vectors are `sqrt(3)` times longer than the conventional cubic reciprocal
basis vectors, so the closest integer-resolution conventional mesh is
11x11x11 (`19/11 = 1.7273`, within 0.28% of `sqrt(3)`).  Both meshes are odd
and therefore sample Gamma in the same parity convention.

Run the complete regression with:

```sh
./run_workflow.sh
```

The runner executes the two calculations sequentially and
`check_equivalence.py` verifies convergence, electron count, insulating
primitive-cell bands, energy per two atoms, and hydrostatic stress.
