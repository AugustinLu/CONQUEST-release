# Monoclinic HfO2: ionic Ewald validation in a general cell

## Purpose

The 12-atom baddeleyite cell has a genuinely non-90-degree monoclinic angle
and chemically distinct Hf and O sublattices. It is therefore a stronger test
than graphite or primitive Si of general-cell ionic electrostatics, local
coordination, force accumulation, and the complete stress tensor.

## Maintained checks

- `./run_ewald_cell_smoke.sh` runs two outer method-2 atom/cell cycles with
  `General.NeutralAtom F`. It requires accepted downhill full-lattice steps,
  convergence of at least one cell cycle below the stress threshold, and
  repeated complete Ewald-state rebuilds for trial lattices.
- `./run_ewald_force_fd.sh` uses CONQUEST's full-force finite-difference
  harness for the x force on a representative Hf atom. The reference analytic
  and numerical forces are 0.007207741844 and 0.007170249319 Ha/a0,
  respectively; the absolute error is 3.75e-5 Ha/a0.
- `./run_ewald_strain_fd.sh` applies all six independent central symmetric
  strains to a deliberately symmetry-broken monoclinic cell. It compares both
  the total DFT stress and the isolated analytic ion-ion stress with energy
  derivatives. The runner requires the largest Ewald error to remain below
  0.01 GPa and the largest total-stress error below 0.10 GPa.

The input uses the canonical keyword `IO.FractionalAtomicCoords`. A future pDOS
stage must include `IO.writeDOS T`.

## Quantitative reference

For strain step 5e-4, the explicit-Ewald contribution agrees in every
component:

| component | analytic ion-ion stress (GPa) | Ewald derivative (GPa) | absolute error (GPa) |
|---|---:|---:|---:|
| xx | 2733.10035 | 2733.10178 | 0.00144 |
| yy | 2751.66934 | 2751.67088 | 0.00155 |
| zz | 2643.32757 | 2643.32889 | 0.00133 |
| xy | 22.89409 | 22.89409 | 0.00000 |
| xz | -289.69574 | -289.69588 | 0.00014 |
| yz | 11.01814 | 11.01812 | 0.00001 |

The maximum error is 0.00155 GPa and the RMS error is 0.00102 GPa. This is
strong evidence that the generalized Ewald energy and all six ionic stress
components use the skew lattice consistently.

The same test exposed and now guards an independent electronic-stress defect:
the full GGA XC tensor was calculated but only its diagonal was accumulated.
After retaining the off-diagonal terms, analytic and finite-difference total
stresses agree to 0.04825 GPa at worst and 0.02501 GPa RMS. In particular,
the monoclinic-plane xz result changes from -0.40078 to -0.93768 GPa, versus
-0.94183 GPa from the energy derivative (0.00415 GPa error).

The coupled cell smoke test exposed a second, independent variable-cell
defect. For SIESTA/ABINIT-format pseudopotentials, the energy shift reported
as the core-correction energy is proportional to `1 / cell volume`. The
pseudopotential grid was rebuilt after a lattice trial, but this scalar was
left at its old-cell value. Its missing 0.07374454 Ha change at a
representative strain almost exactly produced the apparent uphill slope.
Recomputing it after each cell update makes the same trial agree with a
cold-start calculation and restores downhill line searches.

In the current two-cycle reference, the first cell cycle lowers the energy
from -358.70465487 to -358.70841529 Ha and the maximum stress from 8.2732 to
0.0687 GPa. After the next atomic relaxation, the second cell cycle reaches
0.0723 GPa. The run accepts six cell steps and rebuilds the explicit Ewald
state 24 times.

## What this validates

This test now validates repeatable variable-cell Ewald setup, skew-cell
real/reciprocal enumeration, a representative total atomic force, all six
ionic Ewald stress components, all six total PBE stress components, and
coupled method-2 atom/cell mechanics with converged inner cell cycles. The
short two-cycle smoke run does **not** claim a fully converged HfO2 ground
state: its final maximum force is 0.00141 Ha/a0. Equivalent unimodular-cell
invariance, rank reproducibility, a production-quality fully converged
relaxation, and HfO2 band/pDOS post-processing remain future acceptance gates.
