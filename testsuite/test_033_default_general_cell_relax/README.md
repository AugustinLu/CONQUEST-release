# Test 033: default general-cell relaxation

This regression starts primitive silicon from a small symmetric shear for
which every diagonal stress is below the default `0.1 GPa` tolerance while
the `xy` stress is substantially larger.  The Method-1 input deliberately
sets only:

```text
AtomMove.OptCell       T
AtomMove.OptCellMethod 1
```

All other cell-relaxation controls retain their defaults.  General-cell input
handling must therefore enable the full stress tensor and select the
backtracking symmetric-strain minimizer.  The run must not claim convergence
from the diagonal stresses alone, and all six stress residuals must be below
the tolerance at the actual endpoint.

The workflow also runs a one-step Method-2 smoke case.  That case is not a
convergence test; it checks that Method 2 selects the same backtracking cell
step rather than delegating to the diagonal-only safe minimizer.

Run with:

```bash
./run_workflow.sh
```
