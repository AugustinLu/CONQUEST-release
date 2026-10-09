# Independent verification of the Gemini nonorthogonal-cell audit

Date: 2026-10-09 (Asia/Tokyo). Audited source: `6c018155b548bbb9e8121f695a9941384f620fb6`.
The original audit is `AUDIT_REPORT_NONORTHOGONAL_CONQUEST.md` in the parent
workspace. Verification used new calculation directories, checked MPI exit
codes, analytic finite differences, and the existing regression workflows.

## Verdicts

| Audit item | Independent verdict | Correction |
| --- | --- | --- |
| BUG-01 | Valid output omission/ambiguity; the claimed electronic covariance failure is not established by the supplied comparison. | Commit `0773413b`: explicit Cartesian total, reduced coefficients, lattice contributions and quantum vectors. |
| BUG-02 | Valid wrong cell-length driving forces and physical stress modification. The claimed constrained full-strain execution path is unreachable. | Commit `4058b8b3`: keep the physical virial intact; differentiate the full lattice in length coordinates and constrain only optimizer gradients/residuals. |
| BUG-03 | Valid geometry/gradient error; claimed failure to preserve the requested length ratio is false. | Commit `7a059812`: project the true gradient onto each ratio tangent, including pressure; preserve ratios exactly. |
| BUG-04 | Documented, intentional fixed-angle Method-3 parameterization, not an independent defect. Constrained Methods 1/2 also use fixed-angle coordinates. | Clarified the existing warning and input documentation in `4058b8b3`; no change to Method 3's degrees of freedom. |

The audit's assertion that every reported defect was introduced by the fork
is also incorrect. `upstream/develop` at `0fb0a4489d34c4c5a6fbdf8bcb33c8db9ff05253`
contains both Cartesian stress zeroing and ratio averaging. General-cell
support makes that inherited optimizer assumption invalid for its new input
domain. The stress-output modification itself is inherited. The audit's
cited upstream object `d3876067b` is not present in this checkout, so the
provenance comparison uses the available upstream reference and fork history.

## Polarization

Let A contain the lattice vectors as columns, V = det(A), and p the total
reduced ionic plus electronic coefficients. The Cartesian vector is
`P = A p / V`; its quantum vectors are the columns of `A/V`. The old scalar
`p_i |a_i| / V` is a signed lattice contribution magnitude, not a Cartesian
component or a projection of the complete vector onto a lattice vector.
The full vector is now printed when all three electronic directions have
been calculated. Single-direction calculations print only their contribution
and quantum, and explicitly state that a full vector requires `General.PolDir 0`.
Legacy scalar records remain available with their meaning stated explicitly.

The original rotation comparison treated lattice-indexed scalars as Cartesian
components and did not align polarization branches. Its apparent doubling of
a component is nearly one integer polarization quantum. That cannot establish
a failure of the physical observable. A polarization branch is defined modulo
integer lattice quantum vectors; see the primary
[VASP Berry-phase documentation](https://vasp.at/wiki/Berry_phases_and_finite_electric_fields).
The existing test 017's coefficient comparison modulo a quantum is therefore
legitimate, not evidence of concealing a bug. It now also compares the printed
Cartesian vectors after aligning branches.

Fresh 45-degree rotation checks give an energy difference of `2.13e-14 Ha`,
a reduced-coefficient residual of `4.18e-9` modulo the quantum, and a Cartesian
vector residual of `3.895e-11 e/Bohr^2`. The equivalent-cell integer-basis
transformation test gives `1.1284e-7 e/Bohr^2` after branch alignment, within
its finite-grid tolerance.

## Length constraints and physical stress

For Methods 1/2 length-only steps, the actual update is
`A_new = A diag(L_new/L)`, with fixed lattice angles. The strain generator
for length i is `a_i tensor row_i(A^-1) / L_i`. Thus the enthalpy derivative is

```
g_i = [sum_jk stress(j,k) A(j,i) A_inverse(i,k) + p V] / L_i
```

Here `stress` is CONQUEST's Cartesian virial in energy units. The unit-vector
quadratic projection suggested in the audit is not the derivative of this
update for a skew lattice. The inverse-lattice contraction used in Method 3
is the appropriate starting point, with the additional length denominator
for Methods 1/2's length coordinates.

The optimizer now obtains these derivatives without modifying `stress`.
Frozen lengths have zero optimizer gradient, including their pressure term.
Both Method 1 and the Method-2 outer loop use projected free-coordinate
residuals for convergence. The length backtracking minimizer uses the true
enthalpy directional derivative, including pressure and the length denominator.
Physical stresses in `Conquest_out` and extended XYZ retain all components.

The fresh baseline gave a `0.02309896 Bohr` cell difference after a 90-degree
rotation with fixed a. After correction, Methods 1 and 2 agree within
`6.20e-13 Bohr` at both 0 and 2 GPa, and a remains exactly fixed. Static
calculations with `a` and `none` produce identical physical stress tensors.
Extended-XYZ stress was checked against physical output in all 18 final
fixed-length, ratio, uniform-scaling and static cases.

`full_lattice_relax` explicitly requires constraint `none` and full-stress
backtracking. The audit's assertion that an `a` constraint modifies the stress
used by `backtrack_linemin_lattice` describes an execution path that cannot
occur. The reachable constrained length path was nevertheless incorrect and
has been repaired.

## Ratio constraints

For fixed `L_j/L_i = r`, allowed length changes obey `dL_j = r dL_i`.
The tangent is `(1,r)` and the orthogonal projected gradient is

```
g_i_projected = (g_i + r g_j)/(1 + r*r)
g_j_projected = r g_i_projected
```

The inherited average `(g_i+g_j)/(1+r)` does not preserve virtual work and can
produce a nonzero gradient for a pure constraint reaction. The new unit test
fails with exit 6 when compiled against the inherited projector and passes
with the correction. It checks analytic central finite differences, virtual
work, projection idempotence, all ratio aliases, and pure constraint reactions.

The old `update_cell_dims` already preserved each requested ratio algebraically;
that part of BUG-03 is disproved. The new triclinic integration cases preserve
the ratios within `2.22e-16` and agree with rotated copies. The same projection
fix also repairs the documented `volume` option: it means equal relative
scaling of all vectors, including unequal lengths, not equal absolute length
increments and not fixed determinant volume.

## Regression scope and resources

- Production build: Homebrew MPI/gfortran, `make -j4`, OpenMP/BLAS threads limited to 1.
- New test 036: full-vector rotation covariance and all three single-direction modes.
- New test 037: bounds-checked analytic gradients and fresh Method-1/2 integration cases, including nonzero pressure, triclinic ratios and uniform scaling.
- Existing test 017: equivalent-cell polarization plus lattice/stress extended-XYZ metadata, two MPI ranks.
- Existing test 033: default full-strain Method-1 convergence and Method-2 smoke case, one rank. Maximum stress decreased from `0.74251855` to `0.00823880 GPa`.
- Existing test 019: volume/xyz NPT, fixed-angle Method-3 smoke, and Python triclinic MIC utilities, two ranks.
- Additional safe-line-minimizer checks: fixed a, a/b and uniform scaling with unequal lengths.
- Existing fixed-cell Si tests 001/002: diagonalization and Order-N, fresh copies and maintained reference tolerances for energy, forces and stress. Energy errors were `1.97e-10` and `2.30e-9 Ha`. The maintained reader and tolerance functions were loaded directly because pytest was unavailable in the system Python; no pytest suite run is claimed.

Calculations ran locally with at most four CPU cores in aggregate: either four
single-thread build jobs, or simultaneous MPI tests with a total of four
single-thread ranks. No remote machines were needed. Generated calculation
artifacts and logs are in the parent workspace's `audit_validation/`; compact
metrics and source hashes are recorded in `gemini_audit_verification.json`.
The initial focused verification did not run the full repository suite or
production-scale relaxation campaigns. The full-suite follow-up is below.
Passing these cases does not establish accuracy for all cell shapes,
electronic states, basis choices or optimization tolerances.

## Full-suite follow-up before push

All numbered workflows 001–037 were rerun from isolated, fresh checkouts on
2026-10-09: **36 passed; 009 failed its historical stress reference**. The new
036/037 checks and the existing coupled relaxation, polarization, hybrid,
oxide, NPT, blip, and equivalent-cell workflows passed. This is not a claim
that the entire suite is green.

Fresh runs of both the original audited revision `6c018155` and corrected
scientific source `7a059812` on impromptu give exactly the same printed DFT+U
diagonal stresses: `(-13.15193128, -17.85631620, -17.85631620) GPa`. Both pass
the energy and force checks and fail the same stress comparison against
`(-13.14995272, -17.85694357, -17.85694357) GPa` at relative tolerance `1e-4`.
The corrected source reproduces the mismatch on the Mac as well. Reference
data and tolerances were not changed.

The fresh-clone run exposed three test-packaging omissions, now repaired:
the missing combined carbon entrypoint, graphene NPT's stale generated-basis
path, and ignored MoS2 coordinate fixtures. The original MoS2 fixtures were
recovered from the earlier working checkout; its reference metadata matches
the current checkout byte for byte. All three repaired workflows passed.

Both main and post-processing executables were rebuilt. The Mac used
gfortran 16.1.0/Open MPI 5.0.9, three build jobs, one thread per MPI rank,
and at most four CPU cores in aggregate. Impromptu used gfortran 13.3.0/
Open MPI 4.1.6, twelve build jobs and three allocated cores per test shard,
with one OpenMP/BLAS thread per rank. The baseline comparison used a separate
checkout and binary. Scientific source hashes still match the initial
verification. Complete attempt histories and logs remain in the parent
workspace under `audit_validation/full_suite_*`; the combined record is
`audit_validation/full_suite_verification_20261009.json`.

BUG-04 remains a deferred general-cell optimization feature. Method 3's
fixed-angle behavior was retained and passed its existing zirconium workflow.
