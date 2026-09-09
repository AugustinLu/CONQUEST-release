# Fermi-level continuity under tiny strain

This four-point primitive-Si regression checks a numerical discontinuity that
was exposed by the nonorthogonal analytic-stress validation.  It applies four
neighboring positive yy strains, separated by `1e-6`, while fixing the grid at
`32 x 32 x 32`, the diagonalisation mesh at `6 x 6 x 6`, and `Diag.kT` at
`0.001 Ha`.

With the historical `1e-6` electron-count stopping tolerance, the Fermi search
can accept materially different positions inside the Si band gap.  Between
the `1.85e-4` and `1.86e-4` strains, the reported Fermi level jumped by about
`0.00391 Ha` and the energy contained a spurious `5.16e-7 Ha` step.  Tightening
the occupation-number convergence removes both discontinuities without any
stress or grid-formula change.

Run with:

```bash
./run_workflow.sh
```

The check requires the range of the three successive energy increments to be
below `1e-9 Ha` and every neighboring Fermi-level change to be below
`1e-4 Ha`.
