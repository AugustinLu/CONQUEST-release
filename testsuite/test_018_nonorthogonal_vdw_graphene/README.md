# Test 018: nonorthogonal vdW-DFT graphene invariance

This regression exercises the reciprocal-space normalization of the nonlocal
vdW-DFT functional in a physically relevant two-dimensional carbon system.
It is a specialist nonorthogonal-cell gate, not a production graphene binding
calculation: a Gamma-only mesh and modest grid cutoff keep it inexpensive.

`coords_base.dat` is the usual hexagonal graphene primitive cell.
`coords_sheared.dat` describes exactly the same infinite lattice and atomic
positions after the determinant-one integer basis transformation

```text
a1' = a1
a2' = 2 a1 + a2
a3' = a3 .
```

The determinant and physical volume are unchanged, while the product of the
three lattice-vector lengths increases by `sqrt(3)`.  This makes the test
specifically sensitive to the old orthorhombic normalization
`1/(|a1||a2||a3|)`: it must instead use `1/|det(A)|`.

Run with:

```bash
NP=2 ./run_workflow.sh
```

The analyser requires both calculations to converge, confirms the intended
geometric invariants, and compares both the vdW correction and the corrected
Harris-Foulkes energy.  The finite real-space grids differ between the two
basis representations, so the numerical thresholds allow a small integration
residual rather than demanding bitwise equality.

With the committed inputs, the run gives a volume difference below
`1e-12 Bohr^3`, a vector-length-product ratio of `1.73201854`, a
vdW-correction residual of `4.85e-6 Ha`, and a corrected-total-energy residual
of `1.19e-4 Ha`, identical (to `1e-14 Ha`) with one and two MPI ranks.  Both
energy residuals are comfortably below the `2e-3 Ha` finite-grid threshold.

The two-rank default also guards the FFT normalisation of the nonlocal term.
It used to scale by `sqrt(maxngrid)`, the per-process grid array size, instead
of the square root of the total number of grid points.  The vdW correction then
depended on the number of ranks and on the block decomposition: with two ranks
the base and sheared cells gave `0.701388` and `0.697041 Ha` (residual
`4.2e-3 Ha`, a failure), against `0.712575` and `0.712579 Ha` after the fix.

This checks one additional piece of general-cell functionality beyond tests
010--017: nonlocal correlation integration must use the true cell determinant
even when the lattice vectors are strongly skewed.
