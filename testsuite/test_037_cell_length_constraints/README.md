# Cell-length gradients and constraints

`bash run_unit.sh` compiles the production geometry helper with bounds checks
and verifies its gradient against central finite differences of an analytic
rotation-invariant energy plus nonzero pressure. It checks rotated triclinic
lattices and fixed-length constraints, including pressure on frozen lengths.

After building CONQUEST, run:

```
python3 check_relaxation.py --results /tmp/cq-constraints-new-run
```

The integration test uses new directories and checked MPI exit codes. Methods
1 and 2 must preserve fixed `a` and give the same cell trajectory after a
90-degree rotation, at zero and nonzero target pressure. A static calculation
with a constraint must report exactly the same physical stress as one without
it. `--ratios` adds all three ratio constraints and uniform scaling on a
triclinic cell and its rotated copy. `--safe-checks` exercises safe line
minimization for fixed lengths, ratios and uniform scaling. Each run uses one MPI rank and one thread. `--baseline` reports the old
rotation error without requiring the corrected behavior.

Length steps differentiate A diag(L_new/L) directly: dH/dL_i is the contraction
of the physical virial with a_i tensor row_i(A^-1), divided by L_i, plus pV/L_i.
A unit-vector quadratic stress projection is not this length derivative.

Ratio gradients use the orthogonal length-space projector onto (1,r):
(g_i + r g_j)/(1+r^2), including shear through the full lattice derivative.
The unit test checks virtual work, idempotence, all ratio aliases, and a pure
constraint reaction for which the projected gradient must vanish. The
`volume` constraint means uniform relative scaling, including unequal lengths.
