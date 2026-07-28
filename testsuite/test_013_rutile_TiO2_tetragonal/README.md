# Rutile TiO2 tetragonal validation

## Purpose

Rutile is an anisotropic but right-angled tetragonal regression. It does not
by itself test a non-90-degree lattice angle; its role is to check that the
general-cell changes do not regress a well-known non-cubic transition-metal
oxide, and to exercise Ti d / O p projected states.

The six-atom P42/mnm cell uses experimental-scale starting parameters
`a = 4.5937 A`, `c = 2.9587 A`, and oxygen internal coordinate `u = 0.305`.
The available Ti and O ion files use Perdew-Wang LDA, so numerical gaps and
relaxed parameters must be compared to LDA references rather than PBE.

`./run_workflow.sh` performs fixed-cell oxygen-coordinate relaxation,
converged SCF, l-resolved pDOS, and an HPKOT/SeeK-path band calculation.
Disconnected path branches are collapsed to zero plot width and labeled with
combined ticks such as `Z|X`, avoiding blank regions for uncalculated k-lines.

## What this checks

- anisotropic `a != c` handling after the general-cell refactor;
- preservation of the P42/mnm structure and its oxygen internal coordinate;
- non-cubic reciprocal vectors, k-meshes, and the tetragonal HPKOT path;
- forces on a transition-metal oxide;
- the expected O-p valence and Ti-d conduction character in the pDOS;
- absence of orthorhombic/tetragonal regressions caused by the oblique-cell
  implementation.

The validated run reduced the maximum force from `0.0137804` to
`0.00015348 Ha/bohr`, moved `u` from 0.312 to 0.3052583, and produced a direct
LDA path gap of `1.7040 eV`. The SCF contains 48 valence electrons. The plotted
DOS window integrates to 32 because 16 Ti semicore electrons lie below that
window. Compact results are retained in `reference/`.

## What this does not prove

All rutile lattice angles are 90 degrees. This case is a high-value
anisotropic and chemical regression, but it is not direct evidence that
non-90-degree image enumeration or ionic Ewald stress is correct. Primitive
Si and graphite supply the oblique geometry tests; monoclinic HfO2 must
eventually supply the ionic oblique-cell acceptance.
