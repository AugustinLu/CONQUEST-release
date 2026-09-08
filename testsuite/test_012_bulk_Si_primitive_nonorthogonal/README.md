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
  `0.0548 GPa`, RMS error `0.0360 GPa`, and maximum relative component error
  `2.34%`.

Compact summaries and plots are in `reference/`.

## Finite-difference step and cutoff sensitivity

The canonical six-strain check retains its original `5e-4` step and tolerance.
`run_strain_fd.sh` accepts `DELTA` and `GRID_CUTOFF` environment variables so
that numerical derivatives can be checked for stability.  Repeating the sweep
for every tensor component gives the following absolute errors in GPa:

| strain step | xx | yy | zz | xy | xz | yz | maximum |
|---:|---:|---:|---:|---:|---:|---:|---:|
| `1.0e-3` | 0.010321 | 0.030237 | 0.016684 | 0.017736 | 0.025137 | 0.004432 | 0.030237 |
| `5.0e-4` | 0.000279 | 0.054785 | 0.044961 | 0.005067 | 0.051901 | 0.003586 | 0.054785 |
| `2.5e-4` | 0.004107 | 0.107739 | 0.103787 | 0.002066 | 0.000376 | 0.001829 | 0.107739 |
| `1.5e-4` | 0.003241 | 0.000813 | 0.002888 | 0.001091 | 0.000540 | 0.000715 | 0.003241 |
| `1.25e-4` | 0.002553 | 0.000556 | 0.002483 | 0.001151 | 0.000676 | 0.000014 | 0.002553 |
| `1.0e-4` | 0.002103 | 0.001126 | 0.001952 | 0.000701 | 0.000782 | 0.000490 | 0.002103 |

The convergence is strongly non-monotonic: xz improves at `2.5e-4`, while yy
and zz become worse there.  At three neighboring steps from `1.0e-4` through
`1.5e-4`, all six components agree within `0.00325 GPa`.  The behavior
therefore does not divide into diagonal versus shear components, and an
xz-only sweep is insufficient evidence.

At fixed step `5e-4`, increasing the cutoff from 80 to 120 and 160 Ha changes
the yy error from `0.05478` to `0.04893` and `0.05072 GPa`; the corresponding
xz errors are `0.05190`, `0.05483`, and `0.05732 GPa`.  A simple cutoff
increase does not monotonically eliminate either coarse-step discrepancy.

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
out a stable missing analytic stress term at the measured scale.  The
non-monotonic sequence is consistent with numerical finite-grid sampling, but
does not by itself identify one unique numerical mechanism.  The full
machine-readable sweep is stored beside the canonical reference summary.

## What this checks—and what it does not

This case directly checks nonorthogonal geometry, orientation-independent
symmetric-strain optimization, off-diagonal stress, reciprocal-space paths,
bands, pDOS, and equation-of-state consistency against a familiar material.
It does not by itself prove ionic Ewald forces/stress, variable-cell MD, or
behavior for arbitrarily unreduced triclinic bases. Test 011 is reserved for
the demanding ionic monoclinic acceptance.
