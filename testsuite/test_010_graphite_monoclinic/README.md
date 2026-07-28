# Graphite and graphene in hexagonal cells

## Purpose

This is the first end-to-end validation of CONQUEST with lattice vectors that
meet at 60/120 degrees. It contains AB graphite and isolated graphene so that
the same carbon basis can test both a three-dimensional layered crystal and a
two-dimensional slab.

The maintained entry points are:

```bash
./run_cell_relax.sh
./run_graphite_hcp.sh
./run_graphene.sh
```

The cell runner uses `AtomMove.OptCellMethod 2`, which alternates atomic CG
with full-cell CG using the six-component stress and a symmetric-strain
update. The material wrappers call
`run_carbon_band_pdos.sh`, which performs a converged SCF
calculation, writes the data required by `PostProcessCQ`, calculates
angular-momentum-resolved pDOS, follows the conventional hexagonal band path,
and writes SVG and PNG plots. `IO.writeDOS T` is deliberately present: pDOS
post-processing requires it. The generated files are placed below
`band_pdos_results/`.

On macOS, the cell runner defaults to `/usr/sbin/taskpolicy -b`; set
`BACKGROUND_MODE=F` for fast cores. All runners default to two MPI ranks and
reject larger values.

## What this checks

- direct- and reciprocal-lattice construction for a hexagonal metric;
- fractional-to-Cartesian coordinate transforms;
- real-space grids, atom images, partitions, and matrix ranges in an oblique
  cell;
- Monkhorst-Pack sampling and fractional reciprocal-space band paths;
- fixed-cell carbon forces and full-cell symmetric-strain relaxation;
- method-2 alternating atomic and full-cell CG convergence;
- wavefunction export, total DOS, and orbital-projected DOS;
- the graphite bands near K and the graphene Dirac crossing at K.

The literature starting structures are kept in `structures/`. Method 1
provides a useful cell-only validation and reduced the maximum stress from
about 22.30 GPa to 0.0117 GPa in 19 accepted geometry steps while retaining
the hexagonal geometry. Method 2 is the coupled atom/cell acceptance workflow:
the validated two-rank run converged in six outer ionic/cell cycles, reducing
the maximum force from 0.031912 to 0.00019971 Ha/bohr and the maximum stress
from 22.3003 to 0.04311 GPa. Both the fractional coordinates and lattice
changed. In the current compact-basis reference runs, the numerical gaps at K are
approximately 0.052 meV for graphite and 0.493 meV for graphene,
and the DOS integrals recover 16 and 8 valence electrons respectively. These
tiny residual gaps are numerical acceptance signals, not predictions of
physical gaps.

Reference plots from the validated run are in `reference/`.

## What this does not prove

Carbon pseudopotentials used here do not exercise the explicit ionic Ewald
path as strongly as an ionic oxide. This test also does not validate
variable-cell molecular dynamics, spin-orbit coupling, or every possible
unreduced triclinic cell. Those require separate tests. In particular,
monoclinic HfO2 in test 011 remains the intended ionic oblique-cell
acceptance case.
