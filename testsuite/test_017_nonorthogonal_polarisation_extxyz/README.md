# Nonorthogonal polarization and extended-XYZ metadata

## Purpose

This test represents the same displaced primitive-Si crystal with a reduced
60-degree basis and with the determinant-one change `a2' = a1 + a2`.
It validates two specialist paths that historically assumed Cartesian,
orthorhombic cell vectors:

- Resta ionic positions and polarization quantum normalization;
- extended-XYZ lattice and stress metadata.

The ionic polarization now obtains fractional coordinates with the full
inverse lattice. The polarization quantum uses the determinant volume.
Extended XYZ writes the three complete lattice vectors rather than a diagonal
box and normalizes stress with the determinant volume.

## Acceptance

`./run_workflow.sh` performs Gamma-point polarization calculations for both
representations and requires:

- identical determinant volume;
- polarization coefficients related by the integer basis transformation,
  modulo a polarization quantum;
- printed quantum magnitudes equal to `|a_i| / det(A)`;
- all nine extended-XYZ lattice values equal to the input lattice;
- total energies consistent within the finite-grid representation tolerance.

The committed two-rank reference run has identical `277.983664 Bohr^3`
volumes, a `3.02e-4 Ha` finite-grid energy residual, a `2.05e-14 e/Bohr^2`
maximum polarization-quantum error, and a `9.69e-6` maximum transformed
polarization-coefficient residual modulo the quantum.  The maximum extended-XYZ
lattice and stress serialization errors are `4.96e-9 Angstrom` and
`7.93e-7 GPa`, respectively.

This is a specialist geometry regression. Primitive-Si relaxation, stress
finite differences, EOS, bands, and pDOS remain in test 012.
