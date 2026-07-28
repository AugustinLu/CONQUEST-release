# Primitive diamond Si in a nonorthogonal cell

## Purpose

This test represents diamond Si with the two-atom FCC primitive cell rather
than the existing eight-atom conventional cubic cell. Its three primitive
lattice vectors meet at 60 degrees, so it isolates general-cell geometry
without changing the element, pseudopotential, basis, or exchange-correlation
functional used by `test_001_bulk_Si_1proc_Diag`.

This is the foundational nonorthogonal regression: it represents the same
crystal as the established conventional-cell Si test, but does so with two
atoms and three primitive vectors meeting at 60 degrees.

## Workflows

`./run_workflow.sh` performs:

1. fixed-cell atomic CG relaxation from a deliberately displaced basis atom;
2. a converged self-consistent PBE calculation;
3. fixed-density, angular-momentum-resolved pDOS;
4. a fixed-density band calculation on the HPKOT/SeeK-path route
   `Gamma-X-U | K-Gamma-L-W-X`;
5. generation of a combined band/pDOS image and a machine-readable summary.

The additional runners are:

- `./run_eos.sh`: nine-point, third-order Birch-Murnaghan equation of state;
- `./run_cell_relax.sh`: orientation-independent full-cell CG using symmetric
  strain and all six stress components;
- `./run_strain_fd.sh`: all six analytic stress components compared with
  central energy derivatives in a deliberately distorted cell.

`generate_seekpath.py` calls `seekpath.get_path_orig_cell`, which is important:
the returned points are expressed in the reciprocal basis of the exact
CONQUEST input cell. On Augustin's machine, `seekpath` and `spglib` are
available in `/opt/anaconda3/bin/python`.

Disconnected HPKOT branches are plotted at the same x-coordinate and receive
a combined tick such as `U|K`. No horizontal distance is assigned to a jump
for which no k-line was calculated.

On macOS the runner defaults to `/usr/sbin/taskpolicy -b`. The primitive cell
has two atoms, so no more than two MPI ranks are permitted even though
background-policy jobs may otherwise use up to five ranks.

## Validated acceptance signals

- atomic relaxation: maximum force `0.009188 -> 0.00009894 Ha/bohr`;
- indirect path gap `0.7381 eV`, with 8.00046 integrated electrons;
- Birch-Murnaghan equilibrium conventional `a = 5.57896 A`,
  `B0 = 79.90 GPa`, fit RMSE `0.0281 meV/atom`;
- direct cell relaxation `a = 5.57793 A`, within 0.018% of the EOS minimum,
  with final maximum stress about `0.00020 GPa`;
- the 60-degree angles are retained and one-/two-rank endpoints agree to
  approximately `2e-7 A`;
- six-strain stress check: maximum absolute error `0.0646 GPa`, RMS error
  `0.0405 GPa`, and maximum relative component error `2.93%`.

Compact summaries and plots are in `reference/`.

## What this checks—and what it does not

This case directly checks nonorthogonal geometry, orientation-independent
symmetric-strain optimization, off-diagonal stress, reciprocal-space paths,
bands, pDOS, and equation-of-state consistency against a familiar material.
It does not by itself prove ionic Ewald forces/stress, variable-cell MD, or
behavior for arbitrarily unreduced triclinic bases. Test 011 is reserved for
the demanding ionic monoclinic acceptance.
