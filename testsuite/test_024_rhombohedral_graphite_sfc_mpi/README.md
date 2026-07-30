# Test 024: published 3R graphite SFC and MPI acceptance

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

Run with:

```bash
./run_workflow.sh
```

The script never uses more than two MPI ranks and reuses the existing
graphite carbon ion file from test 010.

## Quantitative reference

The maintained run identifies both settings as space group 166 and bulk.
The maximum SFC lattice-normal span error is
`2.77e-7 bohr`. One- and two-rank total energies differ by at most
`3.34e-13 Ha`, their stresses are identical at the printed precision, and
the rhombohedral/hexagonal Ewald energy per atom differs by
`3.67e-11 Ha`.
