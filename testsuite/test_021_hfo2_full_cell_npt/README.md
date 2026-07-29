# Test 021: full-cell NPT dynamics of monoclinic HfO2

This test exercises the six-degree-of-freedom symmetric
`MD.CellConstraint full` Parrinello-Rahman path. The complete Cartesian stress
tensor drives three normal and three shear strains, so both the lattice lengths
and the monoclinic angle can evolve without adding a rigid cell-rotation mode.

The 12-atom P2_1/c HfO2 cell uses the DZP Hf and O PAOs from test 011. Its
initial residual xz stress provides a deliberately shear-sensitive input. The
two-step trajectory checks that:

- all three extended-XYZ stress tensors remain finite and symmetric;
- the determinant volume remains positive;
- the monoclinic beta angle changes measurably;
- the normalized cell metric changes, ruling out purely isotropic scaling;
- the magnitude of the xz shear stress moves toward relaxation.
- a seeded one-step plus restart plus one-step calculation reproduces the
  uninterrupted trajectory, exercising all nine stored entries of the cell
  strain, velocity and force matrices.

Run with up to four MPI ranks:

```bash
NP=4 ./run_workflow.sh
```

This is a deterministic mechanics and execution gate for general-cell NPT. It
is not a claim that two MD steps sample a converged thermodynamic ensemble. A
longer 600 K trajectory, restart equivalence, and timestep-convergence checks
belong to the subsequent statistical validation layer.
