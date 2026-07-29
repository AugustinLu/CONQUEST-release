# Test 022: in-plane NPT dynamics of a 3x3 graphene sheet

This test exercises `MD.CellConstraint xy`, the symmetric three-degree-of-
freedom in-plane Parrinello-Rahman constraint. It permits xx, yy and xy strain
while fixing the Cartesian z direction. The constraint is designed for a slab
whose plane is xy and whose vacuum lattice vector is parallel to z.

The calculation uses an 18-atom 3x3 graphene supercell, a nonorthogonal
hexagonal in-plane lattice and the DZP carbon PAOs from test 010. The two-step
trajectory verifies that:

- the in-plane area responds to the calculated stress;
- the complete vacuum lattice vector is unchanged to output precision;
- the in-plane vectors never acquire z components;
- the cell determinant remains positive;
- the complete calculated stress remains finite and symmetric.

Run with up to four MPI ranks:

```bash
NP=4 ./run_workflow.sh
```

This test is important for nonorthogonal support because an ordinary
three-dimensional NPT barostat would attempt to collapse the artificial
vacuum. It is a short constraint/mechanics regression rather than a converged
finite-temperature graphene simulation.
