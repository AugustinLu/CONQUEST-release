# Exact minimum-image convention for triclinic cells

## Purpose

This source-level regression targets a geometric corner case that ordinary
material cells rarely expose. Independently rounding the three fractional
components does not necessarily return the shortest Cartesian periodic image
when the lattice is strongly skewed or represented by an unreduced basis.

`global_module::mic_vector` now starts from the rounded fractional image and
uses the inverse-lattice row norms to derive a finite integer search box that
is guaranteed to contain every closer lattice translation.

## Workflow

Run:

```sh
./run_exact_mic.sh
```

The runner links a small test directly against CONQUEST's compiled
`global_module.o`. It compares the production routine with exhaustive
translation searches for:

1. a 36.9-degree skew lattice where component-wise rounding is demonstrably
   wrong;
2. many displacements in that cell;
3. an orthogonal lattice written with a large determinant-one shear, testing
   an unreduced but physically equivalent basis.

This test is independent of basis sets, pseudopotentials, SCF convergence, and
MPI layout, so a failure isolates periodic geometry rather than electronic
structure.
