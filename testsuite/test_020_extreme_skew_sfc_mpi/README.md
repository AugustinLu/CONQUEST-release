# Extreme-skew SFC and MPI regression

## Purpose

This test represents primitive diamond Si in both its ordinary FCC primitive
basis and an intentionally unreduced but physically equivalent basis,
`a2' = 8 a1 + a2`.  The large bounding parallelepiped is an adversarial case
for spatial decomposition, exact minimum-image searches, periodic wrapping,
and MPI ownership.

The workflow runs both representations on one and two MPI ranks.  It requires
every calculation to converge, produce a nonempty Hilbert
space-filling-curve partition file, and contain finite energies, forces, and
all nine stress entries.  The SFC classifier must identify both
representations as bulk, and its reported dimensions must match the three
physical spans normal to the lattice faces (the inverse reciprocal-normal
lengths), rather than the Cartesian bounding box or direct-vector lengths.
One- and two-rank results are compared separately for each representation.
The ionic Ewald energy is also required to be invariant under the
determinant-one basis change.

This is a robustness and determinism test, not a converged Si benchmark.  The
finite real-space integration grid is tied to the chosen cell
parallelepiped, so electronic total energies from the reduced and deliberately
unreduced bases are reported but are not required to be identical.

Run with:

```bash
./run_workflow.sh
```

The script never uses more than two MPI ranks.

## Quantitative reference

The maintained run completes all four calculations. One- and two-rank total
energies differ by at most `1.57e-13 Ha`; their Ewald energies are identical
at the printed precision. The determinant-one basis change also preserves the
Ewald energy exactly at the printed precision. The reduced and extreme-basis
electronic energies differ by `3.75e-7 Ha`, which is the expected small
finite-grid representation dependence. Every case writes a nonempty
`hilbert_make_blk.dat`, is classified as bulk, and reports the correct
lattice-normal spans.
