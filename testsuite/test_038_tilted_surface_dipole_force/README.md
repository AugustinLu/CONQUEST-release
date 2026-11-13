# Test 038: surface-dipole forces in a tilted cell

This regression checks the ionic force from the slab dipole correction
(`SC.SurfaceDipoleCorrection T`) when the lattice vector along the surface
normal is not perpendicular to the surface.

The water layer of test 008 keeps its Cartesian positions, but its third
lattice vector is tilted, `a3 -> a3 + a1`.  The surface plane and the slab
height along the normal (15 a0) are unchanged, while `|a3|` becomes 16.04 a0.
The ionic dipole energy depends on the fractional coordinate along the normal,
`s3 = b3 . r`, so its force is along the reciprocal vector `b3` (column 3 of
`recip_lat_vec`).  Before the fix the force used `e3/|a3|`, which is only
correct when `a3` is perpendicular to the surface.

The workflow runs five static calculations (48^3 grid, Gamma point, one MPI
rank): the reference geometry, and +/-0.01 a0 z displacements of the O atom and
of one H atom.  The check requires the analytic z force of each displaced atom
to match the central difference of the Harris-Foulkes energy within
`1e-4 Ha/a0`.

| Binary | Atom | Analytic F_z | Finite difference | Difference |
|---|---|---|---|---|
| before the fix | O | 0.0193984 | 0.0159846 | -3.4e-3 |
| before the fix | H | -0.0095962 | -0.0101783 | -5.8e-4 |
| after the fix | O | 0.0159495 | 0.0159846 | +3.5e-5 |
| after the fix | H | -0.0101710 | -0.0101783 | -7.3e-6 |

The residual after the fix matches the orthorhombic test-008 cell with the
dipole correction on (2.2e-5 for O) and the tilted cell with it off (2.2e-5).

Run with:

```bash
./run_workflow.sh
```

`CONQUEST_BIN`, `MPI_LAUNCHER`, `PYTHON` and `RESULTS_DIR` override the
defaults.  The run takes about four minutes on one core.
