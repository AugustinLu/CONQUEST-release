# Monoclinic HfO2: pending ionic oblique-cell acceptance test

## Purpose

The 12-atom baddeleyite cell has a genuinely non-90-degree monoclinic angle
and chemically distinct Hf and O sublattices. It is therefore a stronger test
than graphite or primitive Si of general-cell ionic electrostatics, local
coordination, force accumulation, and the complete stress tensor.

## Current status

This case is intentionally marked **pending**, not passing. Exploratory static
and coupled atom/cell calculations produced nonzero forces and stresses, but
the old coupled relaxation stopped during line-search backtracking. Its
band/pDOS workflow is not accepted in this checkpoint. No workflow script is
designated as maintained here until the exploratory driver is replaced by the
same staged and checked pattern used by tests 010, 012, and 013.

The input uses the canonical keyword `IO.FractionalAtomicCoords`. A future pDOS
stage must include `IO.writeDOS T`.

## Required acceptance checks

Before this test can be registered as passing, it must demonstrate:

1. static energy invariance under equivalent unimodular representations of
   the same monoclinic lattice;
2. analytic atomic forces against central finite differences;
3. all six analytic stress components against energy derivatives;
4. convergence of fixed-cell atomic relaxation;
5. convergence of coupled atomic and symmetric-strain cell relaxation;
6. one- versus two-rank reproducibility;
7. a SeeK-path/HPKOT band path expressed in the exact input reciprocal basis;
8. Hf-d/O-p resolved pDOS with an electron-count check.

## What it will check

Once accepted, this will be the principal regression for explicit ionic Ewald
summation, skew-cell image enumeration, low-symmetry forces and stress, and
monoclinic band/pDOS post-processing. Until then, no successful result from
tests 010, 012, or 013 should be interpreted as proof that all of those ionic
paths are complete.
