# Monoclinic HfO2: ionic Ewald validation in a general cell

## Purpose

The 12-atom baddeleyite cell has a genuinely non-90-degree monoclinic angle
and chemically distinct Hf and O sublattices. It is therefore a stronger test
than graphite or primitive Si of general-cell ionic electrostatics, local
coordination, force accumulation, and the complete stress tensor.

## Maintained checks

- `./run_ewald_cell_smoke.sh` runs two outer method-2 atom/cell cycles with
  `General.NeutralAtom F`. It checks that explicit ionic Ewald is accepted,
  coupled relaxation is entered, and the complete cell-dependent Ewald state
  is rebuilt after lattice trials. The four-rank reference run survived 31
  rebuilds, including rejected large strains and restoration of the original
  cell.
- `./run_ewald_force_fd.sh` uses CONQUEST's full-force finite-difference
  harness for the x force on a representative Hf atom. The reference analytic
  and numerical forces are 0.007207741844 and 0.007170249319 Ha/a0,
  respectively; the absolute error is 3.75e-5 Ha/a0.
- `./run_ewald_strain_fd.sh` applies all six independent central symmetric
  strains to a deliberately symmetry-broken monoclinic cell. It compares both
  the total DFT stress and the isolated analytic ion-ion stress with energy
  derivatives. The runner requires the largest Ewald error to remain below
  0.01 GPa.

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

The total DFT stress has a separate xz residual: analytic -0.40078 GPa versus
-0.94183 GPa from the energy derivative. Step-size checks at 1e-3 and 2.5e-4
give -0.94201 and -0.94712 GPa, so this is not finite-difference noise. The
isolated Ewald xz derivative agrees to 0.00014 GPa; therefore the remaining
0.54 GPa discrepancy belongs to cancellation among electronic stress terms,
not ionic Ewald.

## What this validates

This test now validates repeatable variable-cell Ewald setup, skew-cell
real/reciprocal enumeration, a representative total atomic force, and all six
ionic Ewald stress components. It does **not** yet validate converged
atom-plus-cell HfO2 relaxation, the remaining electronic xz stress, equivalent
unimodular cell invariance, rank reproducibility, or HfO2 band/pDOS
post-processing. Those remain explicit future acceptance gates rather than
being hidden by a smoke-test pass.
