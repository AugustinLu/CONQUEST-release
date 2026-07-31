# Nonorthogonal blip-basis regression

This test represents the same eight-atom conventional diamond-Si crystal as
test 025 after the determinant-one basis change `a2' = a1 + a2`.  The new
cell has a 45-degree lattice angle and exactly the same volume and physical
atomic positions as the orthorhombic representation.

Unlike test 025, this case performs one blip support-function variation.  It
therefore exercises the general-cell value, Cartesian-derivative, and inverse
blip transforms rather than checking only a fixed initialized basis.  Its
final force calculation also exercises the second-derivative transform.  The
workflow runs on one and two MPI ranks and requires normal SCF convergence,
finite output, the expected electron count, and rank-invariant final energy.

The orthorhombic develop-branch compatibility baseline remains test 025.
Electronic energies from tests 025 and 026 are not required to be identical:
the finite integration grid follows the chosen cell parallelepiped.

The stored quantitative reference is the first maintained result from this
implementation, not an independent external blip calculation.  It is included
to catch later source regressions; the structural evidence for correctness is
the equivalent-cell construction, completion of every transform path, and
one-/two-rank invariance.

Run with:

```bash
./run_workflow.sh
```
