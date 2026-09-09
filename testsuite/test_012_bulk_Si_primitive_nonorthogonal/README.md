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
- six-strain stress check at the canonical `5e-4` step: maximum absolute error
  `0.00570 GPa`, RMS error `0.00373 GPa`, and maximum relative component error
  `0.164%`.

Compact summaries and plots are in `reference/`.

## Finite-difference step and cutoff sensitivity

The canonical six-strain check retains its original `5e-4` step and tolerance.
`run_strain_fd.sh` accepts `DELTA` and `GRID_CUTOFF` environment variables so
that numerical derivatives can be checked for stability.  Repeating the sweep
for every tensor component gives the following absolute errors in GPa:

| strain step | xx | yy | zz | xy | xz | yz | maximum |
|---:|---:|---:|---:|---:|---:|---:|---:|
| `1.0e-3` | 0.013231 | 0.005581 | 0.006141 | 0.008248 | 0.000859 | 0.004929 | 0.013231 |
| `5.0e-4` | 0.003179 | 0.002379 | 0.005698 | 0.003727 | 0.002140 | 0.004083 | 0.005698 |
| `2.5e-4` | 0.001209 | 0.000719 | 0.002967 | 0.000726 | 0.000895 | 0.002327 | 0.002967 |
| `1.5e-4` | 0.000345 | 0.001495 | 0.000245 | 0.000250 | 0.001059 | 0.001213 | 0.001495 |
| `1.25e-4` | 0.000343 | 0.001751 | 0.000160 | 0.000189 | 0.001195 | 0.000512 | 0.001751 |
| `1.0e-4` | 0.000793 | 0.001182 | 0.000690 | 0.000639 | 0.001301 | 0.000008 | 0.001301 |

The errors now decrease to the expected small numerical floor without the
previous factor-of-two growth and abrupt collapse. No diagonal-versus-shear
pattern remains.

The analytic xz total includes symmetric kinetic (`+1.18685 GPa`), S-Pulay
(`+1.77945 GPa`), Phi-Pulay (`-3.33526 GPa`), local (`+2.40136 GPa`),
non-local (`-1.04272 GPa`), XC (`-0.01268 GPa`), ion-ion (`-3.23987 GPa`),
Hartree (`-0.00851 GPa`), and PCC (`+0.05695 GPa`) contributions.  In
particular, the smaller-step xz numerical derivative agrees with the total
that contains the PCC term, ruling out an omitted PCC shear stress despite the
similar size of that term and the coarse-step error.  Verbose finite-difference
energy decompositions move across several kinetic, XC, neutral-atom/pseudo,
and non-local channels; those individual energies are not separately
variational, so their response terms cannot identify one analytic stress
contribution as the cause.  The small-step agreement of every component rules
out a stable missing analytic stress term at the measured scale.

The former non-monotonic sequence came from the Fermi-level search, not from
the analytic stress. Its historical `1e-6` electron-count tolerance allowed
the bisection to stop at different positions inside the Si band gap after an
arbitrarily small strain. Between positive yy strains `1.85e-4` and `1.86e-4`,
the accepted Fermi energy jumped from `-0.18570992` to `-0.18180371 Ha`. This
changed the tiny smeared occupations and produced a spurious `5.16e-7 Ha`
energy step. A `1e-10` electron-count tolerance gives a smooth Fermi energy
near `-0.1837568 Ha` and removes the step without changing any grid or stress
formula. Test 034 is the focused regression for this behavior.

The grid investigation was still useful for locating the trigger. Every
endpoint used the same `32 x 32 x 32` integration grid, and the block, cover,
matrix, PAO, and neutral-atom support topologies were unchanged. Translating
the atoms by a fraction of one grid spacing, selecting a neighboring grid
size, changing the k-point mesh, or changing `Diag.kT` could remove or move the
old jump because each perturbed the eigenvalues enough to choose a different
acceptable Fermi level. Those controls do not identify the grid-selection
algorithm as the cause. The loose Fermi tolerance dates to the 2012
`findFermi` implementation and is also present in upstream master and develop;
the general-cell branch merely exposed it with a sensitive skew-cell test.

The complete before/after evidence is stored in the machine-readable files
beside the canonical reference summary.

## What this checks—and what it does not

This case directly checks nonorthogonal geometry, orientation-independent
symmetric-strain optimization, off-diagonal stress, reciprocal-space paths,
bands, pDOS, and equation-of-state consistency against a familiar material.
It does not by itself prove ionic Ewald forces/stress, variable-cell MD, or
behavior for arbitrarily unreduced triclinic bases. Test 011 is reserved for
the demanding ionic monoclinic acceptance.
