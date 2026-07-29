# Test 019: nonorthogonal NPT molecular-dynamics cell bookkeeping

This one-step primitive-Si regression checks the variable-cell molecular
dynamics paths that previously reconstructed an orthorhombic box from three
lengths.  It uses the default isotropic (`MD.CellConstraint volume`)
Parrinello-Rahman path on a 60-degree primitive cell.

Run with:

```bash
NP=2 ./run_workflow.sh
```

The test verifies that:

- the barostat is initialized from all nine components of the input lattice;
- determinant volume is used;
- the MD frame contains the complete primitive lattice rather than a diagonal
  box;
- reciprocal-grid and density rescaling complete for a skew cell;
- the isotropic barostat preserves normalized cell shape;
- the `xyz` barostat applies diagonal Cartesian strains to complete lattice
  rows rather than to diagonal matrix entries alone;
- the final extended-XYZ cell remains nonorthogonal and has positive volume.
- legacy `AtomMove.OptCellMethod 3` is rejected because its three-length
  optimizer does not synchronize the authoritative lattice state; the
  diagnostic directs users to the fully general method 2.
- the bundled Python MD utilities import with current NumPy/SciPy and their
  generalized RDF/MSD minimum-image calculation agrees with a brute-force
  closest-image search in an adversarial skew cell.

In the committed two-rank reference run, both `volume` and `xyz` complete one
NPT step.  The initial MD-frame lattice is exact to the printed precision.  The
isotropic normalized-shape residual is `2.22e-16`; the final off-diagonal
lattice norms are `7.21` and `7.31 Angstrom` for `volume` and `xyz`,
respectively.

This is deliberately a geometry and execution smoke test, not a statistical
validation of the beta Parrinello-Rahman implementation.  Long-trajectory
ensemble sampling and energy-drift characterization remain general MD
validation topics, independent of the nonorthogonal geometry conversion.
