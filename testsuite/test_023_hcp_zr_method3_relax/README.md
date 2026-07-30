# Test 023: HCP Zr coupled Method 3 relaxation

This example relaxes the two HCP Zr atoms and the cell together with
`AtomMove.OptCellMethod 3`.  The starting lattice is deliberately expanded
(`a = 3.30 Ang`, `c = 5.30 Ang`).  Its two basal vectors meet at 120 degrees.

The `a/b` constraint keeps the basal scale factors equal.  Method 3 may
therefore change `a` and `c` independently, including the `c/a` ratio, while
preserving the 90, 90, and 120 degree HCP angles.  It cannot relax shear or
lattice angles; use Method 1 with `AtomMove.FullStress T` for that task.

Run from this directory with:

```bash
NP=2 ./run_workflow.sh
```

The workflow reuses the PBE `Zr.ion` file from test 015, runs the relaxation,
and checks that the final determinant is positive, the angles are unchanged,
and the `a/b` constraint is satisfied.  The illustrative input uses a
`1 GPa` stress tolerance so that the small example terminates above the
real-space-grid and SCF noise floor; tighten the grid, k-point mesh, electronic
tolerance, and stress tolerance together for production lattice constants.
