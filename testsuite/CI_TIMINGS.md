# CI timings and what was changed (issue OrderN/CONQUEST-release#500)

Status: **checkpoint report, not for merging.** This file is the last commit of the
branch and should be dropped before anything is proposed to OrderN.

Evidence tags: **[M]** measured here, **[R]** read from source/logs/docs, **[J]** judgement.
Raw data: `~/src/ci500_runs/` (not committed): `results.jsonl` (every local run),
`runs/` (every local run directory), `ci_data/` (GitHub job JSON and logs), `tools/` (scripts).

## 1. Summary

| | before (OrderN develop) | after (this branch, on the fork) |
|---|---|---|
| Whole workflow, first job start to last job end | mean 39.8 min, range 30.8-54.6 (20 runs) [M] | 14.6 / 16.6 / 18.0 min (3 attempts, basis + `-j nproc`); 11.8 / 14.2 min (2 attempts, plus job split) [M] |
| Mean job duration (8 jobs) | 28.1 min (160 jobs) [M] | 11.7 min (24 jobs) [M] |
| Test 009 step, median over the 4 configs 1x1 / 1x2 / 2x1 / 2x2 | 1558 / 1290 / 1119 / 908 s [M] | 209 / 174 / 158 / 122 s [M] |

Nearly all of the saving is the test 009 basis change (commit 1). The workflow commits are small.
These are fork runs; runner speed varies from run to run (section 6), so compare ranges, not single numbers.

## 2. Corrections to the starting assumptions

* **The default matrix is 8 jobs, not 4.** `ompGemm_m` has no entry in `exclude`, so every push/PR
  runs `default` and `ompGemm_m` for each of the 4 MPI/OpenMP configurations. All 20 OrderN runs
  have 8 jobs; both kernels have the same timings (test 009: 1142 vs 1145 s mean) [M].
* **Manual dispatch creates 32 jobs.** `gh workflow run makefile.yml --ref <branch>` works from a
  non-default branch (the workflow is registered), but the kernel exclusion does not match the string
  `'false'` that dispatch produces, so all 8 kernels run. I cancelled that run. Push and
  pull_request events give 8 jobs [M]. The fork runs below were triggered by a draft PR **inside the
  fork** (AugustinLu/CONQUEST-release#9), not against OrderN.
* **Queue time is negligible**: median 2 s, max 8 s over 160 jobs [M]. The time is run time.
* **Mac vs runner ratio for test 009** (median of CI / my loaded-Mac pass 1): 7.4 / 9.4 / 6.8 / 8.0
  at 1x1 / 1x2 / 2x1 / 2x2 [M], not 5.5.
* Develop already contains the Fe mass fix in test 009 (`55.850`); branch `fix-test009-fe-mass` is
  not needed for this work [R].

## 3. Per-test timing and decisions

Local = Apple M5 Pro, one run per cell, **machine was loaded** (load average 8-12 on 15 cores, two
CPU SevenNet jobs and Spotlight; section 6), so use local times as upper bounds and for ratios only.
CI = median over 20 OrderN runs x 2 kernels (40 jobs per config) [M].

| test | what it tests | local s (1x1 / 1x2 / 2x1 / 2x2) | CI s (same order) | decision |
|---|---|---|---|---|
| 001 | Si, diagonalisation | 2.9 / 2.2 / 1.9 / 1.6 | 17 / 14 / 10 / 8 | none needed |
| 002 | Si, order-N (L-matrix) | 19.3 / 23.7 / 10.6 / 29.6 | 43 / 64 / 24 / 36 | not touched (see 3.2) |
| 003 | BaTiO3, Resta polarisation | 18.7 / 12.8 / 11.7 / 8.8 | 160 / 127 / 84 / 69 | no safe change found (3.3) |
| 004 | C2H4, PBE0 CRI | 16.7 / 14.6 / 11.6 / 10.6 | 40 / 37 / 26 / 24 | not touched |
| 005 | C2H4, PBE0 with GTO ERI | 62.4 / 39.0 / 35.0 / 23.0 | 169 / 147 / 92 / 82 | not touched (3.4) |
| 006 | C2H4, PBE0 grid ERI | 27.5 / 27.4 / 19.5 / 21.2 | 70 / 64 / 46 / 41 | not touched |
| 007 | CH, spin-polarised PBE0 CRI | 24.1 / 24.3 / 15.3 / 15.6 | 117 / 116 / 68 / 67 | not touched (3.2) |
| 008 | water layer, surface dipole | 4.5 / 3.6 / 3.2 / 2.6 | 21 / 17 / 14 / 12 | none needed |
| 009 | bcc Fe, DFT+U, spin | 211 / 138 / 165 / 114 | 1558 / 1290 / 1119 / 908 | **changed (3.1)** |

Profiles (1x1, `IO.TimingOn T`, `IO.WriteTimeFile F`; tags confirmed in `initial_read_module.f90`
lines 1154-1167) [M]: 009 spends 133 of 192 s in grid integration (area 12); 005 spends 58 of 64 s in
EXX initialisation (areas 1 and 13); 003 spends 14 s of 21 s in integration and 17 s in the energy
minimisation including SCF (28 iterations, one Pulay reset).

### 3.1 Test 009: shorter-range Fe basis (commit 1)

What changes: **only `Fe.ion` and `Conquest_out.ref`**. `Conquest_input` and `bccFe.in` are unchanged.

* Cause of the cost [M]: the CONQUEST "maximum core radius" (nonlocal range) follows the largest PAO
  radius, so a 4s/4p radius of 8.63 bohr in a 5.365 bohr cell makes every grid point overlap many
  atoms. Test with the regenerated basis and the earlier proposed input, 1x1, load about 9:

  | 4s/4p radius (bohr) | max core radius | wall s | SCF its |
  |---|---|---|---|
  | 8.63 (regenerated, 8 orbitals) | 8.63 | 134.6 | 14 |
  | 7.0 | 6.96 | 52.6 | 17 |
  | 6.0 | 6.03 | 22.4 | 15 |
  | 5.5 | 5.48 | 17.1 | 20 (1 reset) |

* Chosen: 6.0 bohr (6.03 after the generator's grid rounding), second zeta 3.5 (3.49), 4p as an ordinary
  polarisation shell with one zeta (7 orbitals, as in the old file). With the **unmodified input** the
  SCF takes 29 iterations in every basis tried, so the plateau and Pulay resets come from the input,
  not the basis; 7.0 bohr was slower (97 s, 35 its). 3s, 3p, 3d (DFT+U acts on 3d zeta 1) are unchanged.
* How it was made [M]: `tools/BasisGeneration` built from this develop, run on the same
  `pseudo-and-pao/PBE/Fe/Fe.in` and `Fe.pot`, with an explicit `Atom.BasisBlock` (radii 2.78; 3.13;
  5.23 2.50; 6.00 3.50; 6.00; `Atom.Perturbative_Polarised F`). The projector part of the new file
  matches the old one to 1e-11 (one line differs in the last digit). **Caveat:** I could not reproduce
  the committed `Fe.ion` exactly (the block interface gave an 8-orbital basis for its radii), so the
  committed file was made some other way. Regenerating with the same procedure is reproducible, but
  the maintainers should confirm they are happy with a basis generated this way.
* Tolerances: unchanged. `Conquest_out.ref` regenerated from a 1x1 run of the new input.
* Local runs, 3 repeats each [M]: 29.4 / 22.1 / 20.9 / 16.8 s at 1x1 / 1x2 / 2x1 / 2x2 against
  211 / 138 / 165 / 114 (loaded pass 1). All 12 pass; smallest margin (tolerance / deviation) 337.
* CI runs on Ubuntu (reference generated on macOS) [M]: all 24 test-009 steps passed; smallest margin 35.7
  (1x2, first attempt), 67.9 on the last attempt. Aim of 10x met.
* Control, DFT+U off (`DM.DFTplusU F`), 1x1 [M]: max force changes 22 % (2234x tolerance), stress 64 %
  (644x), energy only 4x its tolerance. DFT+U is still exercised, and energy remains the weakest probe,
  as before.
* Risk [J]: the basis (and so the physics of the reference) is different, and a 6 bohr 4s/4p range is
  short for production work, though acceptable for a regression test. Needs the other developers'
  agreement. The earlier proposal also changed the input (displacement 0.005 -> 0.03, `SCTolerance`
  1e-6 -> 1e-5); I did **not** include that. On top of the new basis it would save 13 s at 1x1 (29.4 ->
  16.4) and 8 s at 2x2 (16.8 -> 8.9) locally, about 1.5 min on CI at 1x1, but it changes the physics
  tested (6x larger displacement) and loosens a tolerance. Left as an option.

### 3.2 Thin existing margins (not caused by this work) [M]

Smallest ratio tolerance / deviation seen on CI over several runs and both kernels: test 007 1.9-5.4
(once 1.88 at 2x2), test 002 5.4-16, test 003 10.5-15.5. Test 007 uses `minE.SCTolerance 1e-3`, 4 SCF
iterations, and could fail intermittently. Test 002 is also slower with 2 OpenMP threads (CI 43 s at
1x1, 64 s at 1x2). I did not investigate either.

### 3.3 Test 003 (BaTiO3 Resta) [M]

The SCF is erratic (metallic, Gamma-only, 5 atoms; README calls it unphysical on purpose). I scanned
`SC.LinearMixingFactor` (0.3, 0.8), `SC.MaxPulay` (3, 8), `SC.KerkerFactor` (0.03, 0.5),
`SC.KerkerPreCondition F`, `SC.MaxEarly 1` at 1x1 against the **unchanged** reference. Control: 28
iterations. Every variant needed 40+ iterations, three failed to converge in 50, and one converged to a
result 11x outside tolerance (mixing 0.8: margin 0.09). No change proposed. Smearing or a larger cell
would change the test, not just its cost.

### 3.4 Tests 004-007 and 002 [J]

005 and 006 cover two different EXX integral paths (GTO ERI, grid ERI) on the same molecule; 005's cost
is the ERI evaluation, 90 % of its time. A smaller molecule or screening thresholds would reduce the
cost but would stop exercising the 3- and 4-centre integral code or change numerics, so I did not
touch them. 007 has the thinnest margin, so changing it is the wrong direction. These five tests cost
about 2 min per job on CI (1x1) after the 009 change.

## 4. Workflow changes

| commit | change | measured effect | risk |
|---|---|---|---|
| 2 | `make -j $(nproc)` instead of `-j <np>`; one `pip install pytest numpy` (no pip self-upgrade) | Build median, OrderN -> fork 1x1/1x2/2x1/2x2: 73/73/45/44 -> 66/40/74/40 s, 6 jobs per cell. **Mean build 53 s in both.** Not a demonstrated saving; at most 10-30 s for one-rank jobs. | none for numerics |
| 3 (optional) | each configuration split into two parallel jobs: `ground-state` (001, 002, 003, 008, 009) and `exx` (004-007); the exx job checks every test not named for the other group | whole run 11.8 and 14.2 min (2 attempts) vs 14.6-18.0 (3 attempts) without it [M]; 16 jobs, job-minutes 105-114 vs 88-97 | check names change (branch protection); more jobs hitting the apt mirror; difference is within runner noise |

Not done, with reason [J]:
* *Build once, share the binary:* the build is about 50 s of a job that is now about 12 min; every job still
  needs the apt packages, so the gain is aggregate minutes, not wall time.
* *pip cache, apt `--no-install-recommends`:* at most a few seconds; CI installs 41 packages (27.7 MB) with
  reference BLAS/LAPACK 3.10.0 (no OpenBLAS), and changing the package set risks changing the numerics.
* *OpenBLAS and `--bind-to none`:* not tested. The 30 September notes recorded a 2x2 failure (force ~795) whose
  cause is unknown; and the slowest job is 1x1, which neither affects. Not worth the risk for this issue.
* *Other 6 multiply kernels:* untouched (manual-dispatch only).

## 5. Fork CI runs (Ubuntu 22.04 runners, fork run ids)

| run / attempt | commits | jobs | result | wall |
|---|---|---|---|---|
| 42637528249 | unmodified develop | 8 | success | 40.4 min |
| 42649359259 attempts 1, 2, 3 | basis + nproc | 8 | success x3 | 18.0, 14.6, 16.6 min |
| 42652617684 attempts 1, 2 | basis + nproc + split | 16 | success x2 | 11.8, 14.2 min |
| 42649183648 | (dispatch, cancelled) | 32 | cancelled | - |

## 6. Caveats and what was not done

* Local timings were made while two SevenNet CPU sessions and Spotlight used 4-9 cores. Pass 1 of the baseline
  has no load log; later runs log load. Ratios between configurations agree with CI, but absolute local times
  are inflated (test 009 baseline 211 s vs 189 s measured earlier on a quieter machine). **No clean-machine
  pass has been done.**
* Runner speed varies: `Install Dependencies` took 19-30 s normally but 130-260 s in 4 of about 50 fork jobs
  (slow Azure mirror downloads); a few jobs run 2x slower than others for the same work. Fork samples are 2-3
  per variant, so differences of a few minutes between variants are not established.
* Only the `default` and `ompGemm_m` kernels were run. No Ubuntu local timings. No repeated OpenBLAS or binding tests.
* The post-change CI timing of test 009 on CI is 6-9x better, but only 24 jobs were sampled.
* Nothing was pushed to OrderN; no PR to OrderN exists.
