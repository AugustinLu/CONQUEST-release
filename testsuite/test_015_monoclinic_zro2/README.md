# Monoclinic baddeleyite ZrO2

## Purpose

This test adds a second genuinely monoclinic ionic oxide after HfO2, using a
different transition-metal pseudopotential and basis. The conventional
`P2_1/c` cell contains four formula units (12 atoms), three independent `4e`
orbits, and a non-right beta angle. It therefore exercises:

- full-matrix fractional/Cartesian transforms during atomic relaxation;
- explicit ionic Ewald electrostatics in a skew cell;
- restoration and detection of the exact monoclinic space group;
- reciprocal paths generated in the exact CONQUEST input basis;
- a long, disconnected HPKOT path without artificial white-space jumps;
- Zr `4d` and O `2p` orbital projections.

The starting lattice follows the room-temperature neutron-diffraction scale
(`a = 5.1505 A`, `b = 5.2116 A`, `c = 5.3173 A`, beta near 99 degrees)
reported in the
[NIST Structural Ceramics Database](https://srdata.nist.gov/CeramicDataPortal/Scd/Z00179).

## Workflow

Run:

```sh
NP=2 ./run_workflow.sh
```

At night this 12-atom case may use `NP=4`. On battery, set
`BACKGROUND_MODE=T` to place the MPI job under `taskpolicy -b`.

The five stages are:

1. fixed-cell CG relaxation of all 12 atoms;
2. exact `P2_1/c` orbit restoration followed by a tighter SCF calculation;
3. fixed-density, angular-momentum-resolved pDOS with `IO.writeDOS T`;
4. fixed-density bands on the automatically generated HPKOT/SeeK-path route;
5. a combined band/pDOS plot and machine-readable acceptance summary.

`RESUME_RELAX=T` reuses a completed relaxation if a later post-processing
stage was interrupted.

## Validated reference

The four-rank reference gives:

- maximum force `0.00627062 -> 0.00039986 Ha/a0`;
- 96.000022 SCF electrons;
- SeeK-path space group 14, `P2_1/c`, Bravais label `mP1`;
- 241 calculated path k-points;
- indirect path gap `3.37893 eV`;
- minimum direct path gap `3.45564 eV`;
- upper-valence O-p weight `27.5661`, versus Zr-d weight `2.8416`;
- low-conduction Zr-d weight `19.9757`, versus O-p weight `2.5064`.

The O-p valence and Zr-d conduction fingerprints agree with the established
electronic-structure description of monoclinic zirconia
([French et al., 1988](https://doi.org/10.1016/0378-4363(88)90099-X)).
The numerical gap is a scalar PBE/basis regression value, not a
quasiparticle-gap prediction.

The maintained plot, relaxed coordinates, SeeK-path metadata, and JSON
summary are stored in `reference/`.

## Scope

This case validates internal-coordinate relaxation and electronic
post-processing at the experimental cell. It intentionally does not claim
zero pressure: the final stress remains several GPa because the lattice is
fixed. Full atom-and-cell method-2 mechanics, Ewald strain derivatives, and
equivalent-cell invariance are tested more directly by test 011.
