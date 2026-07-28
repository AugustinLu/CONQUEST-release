# Bulk 2H-MoS2 in a hexagonal cell

## Purpose

This six-atom P6_3/mmc case is the next nonorthogonal regression after
graphene, graphite, primitive Si, rutile TiO2, and monoclinic HfO2. Its two
in-plane lattice vectors meet at 120 degrees, while its long c axis contains
two S-Mo-S layers. It therefore checks the general-cell implementation with a
layered transition-metal compound and a much richer PAO basis.

The starting experimental-scale cell uses `a = 3.160 A`, `c = 12.280 A`, and
the sulfur 4f coordinate `z = 0.621`. The maintained ion files are generated
from the in-tree PBE Mo and S pseudopotentials with the standard medium PAO
bases. Mo has 14 valence electrons and includes semicore states; the six-atom
cell therefore contains 52 valence electrons.

## Incremental acceptance gates

`./run_scf_smoke.sh` is the first gate. It runs a fixed-cell PBE SCF
calculation on a 4x4x2 gamma-centred mesh and requires:

- convergence to `1e-8`;
- the expected 52-electron count;
- a complete symmetric stress tensor in the 120-degree cell;
- no general-cell indexing or MPI failure.

The remaining optional extension is:

1. an optional dispersion-aware c-axis cell test, kept distinct from plain
   PBE because interlayer binding is not described reliably without a
   dispersion treatment.

The internal relaxation, converged SCF, l-resolved pDOS, HPKOT bands, and
orbital acceptance checks are now implemented by `./run_workflow.sh`.

## Validated reference

The maintained four-rank result gives:

- sulfur internal coordinate `z: 0.615000 -> 0.62118869`;
- maximum force `0.02736402 -> 0.00019569 Ha/bohr` in nine CG steps;
- P6_3/mmc space group 194 from SeeK-path after relaxation;
- 309 band-path k points on
  `Gamma-M-K-Gamma-A-L-H-A | L-M | H-K`;
- VBM at Gamma and CBM 47.1% along K to Gamma;
- indirect scalar-PBE path gap `0.88044 eV`;
- minimum direct path gap `1.70518 eV`;
- Mo d weight larger than S p weight over the first 2 eV of the conduction
  band (`5.484` versus `2.874` in the broadened pDOS integral).

The exported DOS window integrates to 36.0017 occupied states. This is
intentional: the SCF contains 52 valence electrons, while 16 Mo 4s/4p
semicore electrons lie below the `-1.2 Ha` post-processing window.

The lattice scale follows the single-crystal refinement of
[Schönfeld, Huang, and Moss (1983)](https://doi.org/10.1107/S0108768183002645).
The indirect bulk-gap fingerprint is consistent with the first-principles
layer-evolution analysis of
[Das, Pandey, and Mahadevan (2014)](https://doi.org/10.1103/PhysRevB.90.205420).
These are qualitative validation targets: the present calculation is
scalar-relativistic PBE with a finite PAO basis, not a quasiparticle or
spin-orbit calculation.

## What this checks in the nonorthogonal implementation

This case exercises 120-degree real- and reciprocal-lattice transformations,
hexagonal k meshes and paths, periodic image enumeration, transition-metal d
projectors, partial-core corrections, and strongly anisotropic stress. It
does not replace the ionic-Ewald finite differences in test 011 or establish
spin-orbit accuracy; scalar-relativistic MoS2 is the intended baseline.

Compact machine-readable results, the relaxed coordinates, and the combined
band/pDOS image are retained in `reference/`.
