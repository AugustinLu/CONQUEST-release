# Test 024: published 3R graphite SFC, MPI, and band acceptance

## Purpose

This test uses the experimentally reported 3R rhombohedral graphite
structure rather than an artificial shear.  The primitive cell has two
carbon atoms, equal edges of 3.635 Angstrom, and three exceptionally acute
39.49-degree angles.  Carbon occupies the `2c` positions
`+(0.164,0.164,0.164)` and `-(0.164,0.164,0.164)`.

The structure is from H. Lipson and A. R. Stokes, *The Structure of
Graphite*, Proceedings of the Royal Society A **181**, 101-105 (1942),
doi:`10.1098/rspa.1942.0063`, and is catalogued as Crystallography Open
Database entry 1200018.

## Maintained checks

The generator constructs both published settings of the same crystal:

- the two-atom primitive rhombohedral cell;
- the equivalent six-atom R-centred hexagonal cell.

Before CONQUEST is run, spglib must identify both settings as
`R-3m` (space group 166), their cell volumes must have the exact 3:1 ratio,
and their volumes per atom must agree.

Each representation is then run on one and two MPI ranks.  The analyser
requires:

- bulk SFC classification;
- the reported SFC spans to equal the inverse reciprocal-normal lengths;
- a nonempty Hilbert partition file and finite energies, forces, and all
  nine stress entries;
- rank-invariant total and Ewald energies and stress;
- equal ionic Ewald energy per atom in the rhombohedral and hexagonal
  settings.

The two-atom primitive cell also supplies a separate, denser
`8 x 8 x 8` self-consistent density for:

- carbon-resolved pDOS on the same mesh;
- fixed-density bands along the symmetry-derived HPKOT/SeeK-path route for
  the published `R-3m` cell;
- a combined band/pDOS plot and machine-readable validation summary.

The plotted band eigenvalues are not broadened.  Gaussian broadening applies
only to the DOS/pDOS and defaults to `0.005 Ha` (`0.136 eV`), slightly
narrower than the `0.006-0.010 Ha` widths used by the earlier band/pDOS
tests.  The electronic-structure checks require the expected number of path
points, two carbon pDOS files, an eight-electron DOS integral, finite band
metrics, and carbon `p` character to dominate within 2 eV of the Fermi
level.

Run with:

```bash
./run_workflow.sh
```

The script never uses more than two MPI ranks, reuses the existing graphite
carbon ion file from test 010, and accepts `ELECTRONIC_MESH`,
`BAND_POINTS`, and `PDOS_SIGMA` environment overrides.

## Quantitative reference

The maintained run identifies both settings as space group 166 and bulk.
The maximum SFC lattice-normal span error is
`2.77e-7 bohr`. One- and two-rank total energies differ by at most
`3.34e-13 Ha`, their stresses are identical at the printed precision, and
the rhombohedral/hexagonal Ewald energy per atom differs by
`3.67e-11 Ha`.

The electronic-structure stage produces 18 bands at 241 k points.  With the
maintained SZP, 60-Ha-grid, `8 x 8 x 8` setup, the sampled HPKOT path gap is
`0.0538 eV`; this is a regression value rather than a converged prediction
for graphite's semimetallic overlap.  The broadened DOS integrates to
exactly eight electrons at the Fermi level, and the integrated carbon
`p` weight within `-2` to `+2 eV` is about 480 times its `s` weight.
