#!/usr/bin/env python3
"""Generate matching LaTeX and PDF engineering reports for the CONQUEST branch."""

from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    LongTable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
TEX_PATH = OUT / "nonorthogonal_cell_implementation_report.tex"
PDF_PATH = OUT / "nonorthogonal_cell_implementation_report.pdf"

BASELINE = "34de2d610eec5fefce834cfd469b5f3354d5a9ef"
FEATURE_HEAD = "curated checkpoint based on 7100d69d"
BRANCH = "feature/general-nonorthogonal-cells"


def P(text):
    return ("p", text)


def B(*items):
    return ("bullets", list(items))


def C(text):
    return ("code", text)


def T(headers, rows, widths=None):
    return ("table", headers, rows, widths)


def F(filename, caption):
    return ("figure", filename, caption)


def Q(title, text):
    return ("callout", title, text)


def H(title):
    return ("subheading", title)


def PB():
    return ("pagebreak",)


SECTIONS = [
    (
        "Executive summary",
        [
            Q(
                "Audit conclusion",
                "This branch is a substantial and valuable architectural advance, but it is not yet ready to be represented as complete triclinic physics support. The core data model, reciprocal-space transforms, real-space grid placement, periodic image translations, force/stress assembly, and symmetric-strain cell relaxation have moved decisively toward a general lattice formulation. Graphite, graphene, primitive Si, and rutile now provide converged physics evidence. Specialist paths and the ionic monoclinic HfO2 acceptance case remain bounded follow-up work.",
            ),
            P(
                "The comparison baseline throughout this report is David Bowler's merge commit 34de2d61, dated 2026-07-09, not the accidental develop-branch commit. Before adding the curated examples and report, the tracked source/input comparison covered 39 files, 2,754 insertions, and 2,055 deletions. Ignoring whitespace, the delta was approximately 1,889 insertions and 1,190 deletions. The former whole-file EXX whitespace replacement has been removed from the checkpoint."
            ),
            H("What has been achieved"),
            B(
                "A full 3 by 3 direct lattice matrix, its inverse, reciprocal lattice, determinant volume, and vector lengths are now available as central state.",
                "Cartesian-to-fractional wrapping and reusable periodic image operations replace many independent x/y/z box-length corrections.",
                "Reciprocal k-points are converted with the general A^{-T} transform rather than three scalar divisions.",
                "Integration-grid blocks and points are placed by fractional displacement along lattice vectors.",
                "AABB construction and Hilbert-curve offsets allow skewed parallelotopes with negative Cartesian extents to enter the spatial decomposition.",
                "Periodic group and cover translations use integer image counts multiplied by lattice vectors, avoiding boundary round-off and diagonal-cell assumptions.",
                "Force and stress loops now propagate off-diagonal components through many Pulay, local, nonlocal, Hartree, and pseudopotential contributions.",
                "Cell changes preserve fractional atomic positions and reciprocal fractional coordinates, fixing the earlier non-affine update bug.",
                "A full-lattice backtracking line search now applies an orientation-independent symmetric strain, (I + alpha D) A, using all six independent stress components.",
                "Graphite and graphene SCF, band-structure, total DOS, and l-resolved pDOS workflows now run reproducibly on two MPI ranks and recover the expected K-point crossings.",
                "Primitive two-atom Si passes atomic relaxation, bands/pDOS, Birch-Murnaghan EOS, direct full-cell relaxation, and all-six-component stress finite differences.",
                "Rutile TiO2 passes fixed-cell oxygen relaxation and provides a transition-metal-oxide band/pDOS regression.",
            ),
            H("What is not yet confirmed"),
            B(
                "Static Ewald setup now receives the complete lattice, but cell-changing calculations still need audited rebuilding of cached real- and reciprocal-space Ewald lists plus force/stress finite differences.",
                "The polarization path still derives fractional coordinates by component-wise division by vector lengths and computes volume as a product of lengths.",
                "The vdW-DFT path still uses the product of lattice-vector lengths for reciprocal volume and scalar Nyquist estimates.",
                "Some legacy cell-optimization and MD routines retain diagonal scaling or product-of-length volume formulas.",
                "The fractional rounding MIC is not guaranteed to return the Euclidean shortest image for strongly skewed triclinic cells.",
                "The HfO2 full-lattice smoke calculation reached a backtracking failure; this is evidence of an active algorithmic issue, not a passing validation.",
                "Monoclinic HfO2 is deliberately documented as pending and is not registered as a passing regression.",
            ),
            H("Recommended release claim"),
            P(
                "For the eventual pull request, describe this work as enabling general non-orthogonal lattice infrastructure with validated hexagonal and primitive-rhombohedral operation, including reciprocal-space workflows and symmetric-strain cell relaxation. Reserve the stronger claim of complete triclinic and ionic variable-cell support until HfO2, specialist energy terms, molecular dynamics, and exact minimum-image handling pass their dedicated validation matrix."
            ),
        ],
    ),
    (
        "Checkpoint physics validation",
        [
            H("Graphite and graphene"),
            P(
                "The maintained carbon workflow performs SCF, fixed-density wavefunction export, PostProcessCQ pDOS, and line-mode bands. It includes IO.writeDOS T, uses the canonical IO.FractionalAtomicCoords keyword, and rejects more than two MPI ranks. The numerical K gaps are 0.052 meV for AB graphite and 0.493 meV for graphene; the DOS integrals recover 16 and 8 valence electrons. Cell-only graphite relaxation at fixed fractional atomic coordinates reduced the maximum stress from 22.3003 GPa to 0.011651 GPa in 19 accepted steps."
            ),
            P(
                "The first diagnostic used OptCellMethod 1, which correctly performs cell-only relaxation and therefore left fractional atomic coordinates unchanged. With OptCellMethod 2, the two-rank coupled run converged in six outer ionic/cell cycles: maximum force fell from 0.03191205 to 0.00019971 Ha/bohr, maximum stress fell from 22.300316 to 0.043113 GPa, enthalpy fell by 0.01079614 Ha, and both the lattice and fractional coordinates changed."
            ),
            H("Primitive diamond Si"),
            P(
                "The two-atom FCC primitive cell has three 60-degree lattice angles and is the foundational comparison with conventional-cell Si. Atomic relaxation reduced the maximum force from 0.009188 to 0.00009894 Ha/bohr. The band workflow gives an indirect path gap of 0.7381 eV and integrates 8.00046 electrons."
            ),
            P(
                "A nine-point third-order Birch-Murnaghan fit gives conventional a0 = 5.57896 A, B0 = 79.90 GPa, and 0.0281 meV/atom fit RMSE. Direct symmetric-strain cell relaxation gives a = 5.57793 A, within 0.018 percent of the EOS minimum, while retaining 60-degree angles. The final maximum stress is approximately 0.00020 GPa and one-/two-rank endpoints differ by only about 2e-7 A."
            ),
            P(
                "Central energy derivatives for xx, yy, zz, xy, xz, and yz strains were compared with the analytic stress tensor in a deliberately distorted cell. The maximum absolute error is 0.0646 GPa, RMS error is 0.0405 GPa, and the worst relative component error is 2.93 percent. The analytic tensor is exactly symmetric at printed precision."
            ),
            H("Rutile TiO2"),
            P(
                "Rutile is anisotropic but right-angled, so it checks non-cubic regressions rather than non-90-degree geometry directly. Fixed-cell relaxation moves oxygen u from 0.312 to 0.3052583 and lowers the maximum force from 0.0137804 to 0.00015348 Ha/bohr. The LDA path gap is 1.7040 eV, with O-p valence and Ti-d conduction character. The SCF has 48 valence electrons; the chosen DOS window contains 32 because 16 Ti semicore electrons lie below it."
            ),
            H("Monoclinic HfO2"),
            Q(
                "Pending acceptance",
                "HfO2 remains the demanding ionic, genuinely monoclinic gate. Exploratory calculations produced nonzero forces and stress but coupled relaxation stopped during line-search backtracking. It is not registered as a passing test. Acceptance requires static basis invariance, atomic-force finite differences, all-six stress finite differences, coupled relaxation, MPI reproducibility, and checked bands/pDOS.",
            ),
        ],
    ),
    (
        "Repository history and branch recovery",
        [
            H("Observed history"),
            T(
                ["Reference", "Commit", "Meaning"],
                [
                    ["Bowler baseline", "34de2d61", "True develop tip before the accidental feature commit."],
                    ["Accidental commit", "7100d69d", "Feature commit made directly on develop and already visible as origin/develop."],
                    ["New local branch", BRANCH, "Preserves 7100d69d and the current dirty working tree."],
                    ["Local develop", "34de2d61", "Restored to Bowler's baseline."],
                    ["origin/develop", "7100d69d", "Not force-updated by this work; remote correction still requires an explicit decision."],
                ],
                [3.1 * cm, 3.0 * cm, 9.4 * cm],
            ),
            C(
                "34de2d61  develop\n"
                "    |\n"
                "    +-- 7100d69d  feature/general-nonorthogonal-cells\n"
                "                    origin/develop (still points here)\n"
                "                    + curated source, examples, and evidence"
            ),
            P(
                "The local repair was deliberately recoverable. No commit was discarded: the feature branch continues to name 7100d69d, while the local develop pointer was moved back to the Bowler baseline. The working tree was not reset, cleaned, or stashed, so all follow-up source edits and generated evidence remain present. No remote history was rewritten."
            ),
            H("Initial audit scope"),
            T(
                ["Layer", "Files", "Raw change", "Interpretation"],
                [
                    ["7100d69d versus 34de2d61", "8", "+167 / -213", "Initial conversion, constraint MIC work, I/O/grid changes, plus debug output."],
                    ["Working tree versus 7100d69d", "36", "+3,684 / -2,935", "Most of the present feature, stress, grid, and cell-relaxation work."],
                    ["Combined versus 34de2d61", "39", "+3,828 / -3,125", "Current auditable implementation."],
                    ["Combined, whitespace ignored", "38", "+1,891 / -1,188", "Better estimate of semantic change."],
                ],
                [4.0 * cm, 1.4 * cm, 3.0 * cm, 7.1 * cm],
            ),
            Q(
                "Pull-request hygiene",
                "This checkpoint performs the first curation step: generated calculation trees and local binaries are excluded, the EXX whitespace-only replacement is dropped, premature HfO2 pytest registration is removed, and compact inputs, summaries, plots, and explicit validation contracts are retained. Future physics changes should now be committed one capability and one corresponding test at a time.",
            ),
        ],
    ),
    (
        "Scope, terminology, and lattice convention",
        [
            H("Direct lattice"),
            P(
                "The implementation now treats the simulation cell as a matrix A whose columns are the three direct lattice vectors a1, a2, and a3. A Cartesian position r and fractional coordinate s are related by r = A s and s = A^{-1} r. The signed cell volume is det(A), while physical volume is |det(A)|. This convention is explicitly documented in global_module and is used by the new reciprocal and grid helpers."
            ),
            C(
                "A = [ a1  a2  a3 ]\n"
                "r = A s\n"
                "s = inverse(A) r\n"
                "V = abs(det(A))"
            ),
            H("Reciprocal lattice"),
            P(
                "Fractional reciprocal coordinates q are converted to Cartesian wave vectors with k = 2 pi A^{-T} q. The reverse operation is q = A^T k / (2 pi). These transforms replace the former orthorhombic expressions kx = 2 pi qx / Lx and corresponding y/z formulas. This change is essential for correct band paths, Monkhorst-Pack meshes, FFT reciprocal vectors, and density-response derivatives in skewed cells."
            ),
            H("Real-space grid"),
            P(
                "A grid point indexed by integer triplet n is no longer interpreted as three independent Cartesian offsets. Its location is a fractional combination of the lattice columns. Block origins and point offsets therefore carry the off-diagonal components of A automatically. Grid-cell volume is det(A)/(Nx Ny Nz), and grid spacing summaries use the norms of the direct lattice columns divided by the respective grid counts."
            ),
            H("Periodic wrapping and minimum image"),
            P(
                "General wrapping is performed by converting to fractional coordinates, subtracting floor(s) for [0,1) wrapping, and transforming back. Displacements use s - anint(s) to place each fractional component in approximately [-1/2,1/2). This is exactly equivalent to the usual minimum-image convention for orthogonal cells and many moderately skewed cells."
            ),
            Q(
                "Important geometric limitation",
                "Independent rounding of fractional components is not a mathematically exact closest-vector solution for every triclinic lattice. For sufficiently skewed or unreduced cells, a neighboring image outside the component-wise rounded cube can be shorter in Euclidean distance. A production triclinic MIC should inspect nearby lattice translations, use a reduced cell, or apply a shortest-vector algorithm.",
            ),
            H("Meaning of cell_vec_len"),
            P(
                "cell_vec_len(i) is the Euclidean norm of lattice column i. It is useful for reporting, approximate grid-count selection, and some cutoff estimates. It is not a substitute for the matrix or determinant when computing Cartesian fractional coordinates, volume, reciprocal vectors, Ewald sums, polarization, or affine deformations. Several remaining defects arise precisely where the new length array was substituted mechanically for the old rcellx/y/z scalars."
            ),
        ],
    ),
    (
        "Central lattice infrastructure",
        [
            H("global_module.f90"),
            P(
                "The global state now includes lat_vec, lat_vec_inv, recip_lat_vec, cell_vol, and cell_vec_len. New reusable routines invert_3x3, wrap_into_cell, mic_coords, mic_vector, fractional_recip_to_cart, cart_recip_to_fractional, lattice_grid_block_origin, and lattice_grid_point_offset consolidate operations that were previously duplicated and orthorhombic."
            ),
            C(
                "fractional = matmul(lat_vec_inv, cartesian)\n"
                "fractional = fractional - floor(fractional)\n"
                "cartesian  = matmul(lat_vec, fractional)\n\n"
                "k_cart = 2*pi*matmul(transpose(lat_vec_inv), q_fractional)"
            ),
            P(
                "Centralization is one of the strongest design improvements in the branch. It reduces the chance that each force, density, or partitioning module implements subtly different boundary logic. The helpers also establish a single column-vector convention that can be tested independently."
            ),
            H("dimens_module.f90"),
            P(
                "The scalar supercell representation is replaced by r_super_vec and r_super_vec_inv. Volume is computed from the full determinant, grid-point volume follows from the determinant, and grid-count estimates use lattice-vector norms. The squared length scalars remain for compatibility with code that still expresses spherical bounds using one length per lattice direction."
            ),
            H("Initialization and state synchronization"),
            P(
                "initialisation_module, control, io_module, and initial_read_module were updated so the direct lattice, inverse, reciprocal lattice, vector norms, and determinant are initialized together. This is critical: a valid general-cell implementation cannot tolerate one module updating lengths while another retains a stale inverse or volume."
            ),
            Q(
                "Required invariant",
                "Every cell-changing path must update A, A^{-1}, A^{-T}, vector norms, determinant volume, grid-point volume, k-points, FFT reciprocal vectors, charge-density normalization, atom coordinates, and any cached partition geometry as one transaction. The branch implements most of this in update_lattice_vectors, but older cell-changing paths still need consolidation around that routine.",
            ),
        ],
    ),
    (
        "Input, output, and reciprocal-space handling",
        [
            H("Coordinate parsing"),
            P(
                "io_module and initial_read_module now retain off-diagonal components from coordinate files and PDB CRYST1-derived cells rather than collapsing the cell to three lengths. Fractional atomic coordinates are transformed through the full lattice. Output routines have been adjusted to print matrix-based cell information and, in the extended XYZ path, the full stress tensor."
            ),
            H("K-point conversion"),
            P(
                "Explicit k-points, line-mode band paths, and Monkhorst-Pack points pass through fractional_recip_to_cart. Diagnostic output temporarily converts them back with cart_recip_to_fractional and then restores Cartesian values. This removes a concrete historical bug in which all three printed components were scaled with rcellx and makes hexagonal K paths meaningful."
            ),
            H("Band workflows"),
            P(
                "The graphite and graphene workflows now perform a self-consistent density calculation, a single fixed-density diagonalization that writes a clean wavefunction set for projected DOS, PostProcessCQ l-resolved pDOS, and a fixed-density line-mode band calculation. They use two MPI ranks, literature-like cells, reciprocal paths Gamma-M-K-Gamma-A for graphite and Gamma-M-K-Gamma for graphene, and k meshes that explicitly contain K."
            ),
            H("Remaining output defect"),
            P(
                "At least one io_module output path still reports volume as cell_vec_len(1)*cell_vec_len(2)*cell_vec_len(3). This equals the determinant only for orthogonal cells. Reporting and metadata should use cell_vol consistently, otherwise downstream tools can receive a numerically plausible but wrong volume."
            ),
        ],
    ),
    (
        "Integration grids, FFTs, and spatial decomposition",
        [
            H("Grid block and point geometry"),
            P(
                "PAO_grid_transform_module, blip_grid_transform_module, density_module, pseudo_tm_module, pseudopotential.module, force_module, and related paths replace scalar block origins and point spacings with lattice_grid_block_origin and lattice_grid_point_offset or equivalent vector combinations. This is the core change that allows localized orbitals, densities, local potentials, projectors, and force integrals to sample the same skewed physical grid."
            ),
            H("FFT reciprocal vectors"),
            P(
                "fft_module constructs reciprocal vectors from A^{-T} and updates Nyquist/grid quantities using vector norms. XC gradient paths already differentiate using recip_vector components; once recip_vector is correct, the Cartesian density gradients inherit the general reciprocal geometry without needing separate cell formulas."
            ),
            H("Parallelotope AABB"),
            P(
                "set_blipgrid_module computes the eight corners of a grid or localization parallelotope and derives cell_min and cell_max. This replaces the assumption that the simulation cell occupies [0,Lx] x [0,Ly] x [0,Lz]. A skewed cell can extend into negative Cartesian x or y even when all fractional coordinates are nonnegative, so the AABB is required for safe allocation and binning."
            ),
            H("Space-filling curve offsets"),
            P(
                "sfc_partitions_module stores cell_min and subtracts it before mapping positions to nonnegative Hilbert-grid indices. Image atoms are shifted consistently. This is a necessary partner to the AABB work: without it, negative Cartesian corners would become negative or out-of-range curve indices."
            ),
            H("Cover and group translations"),
            P(
                "cover_module, UpdateInfo_module, UpdateMember_module, primary_module, S_matrix_module, and atom_dispenser_module increasingly represent periodic translations as integer image counts multiplied by complete lattice vectors. The use of integer image counts also removes floating-point ambiguity for atoms exactly on group-cell boundaries."
            ),
            Q(
                "Boundary arithmetic review",
                "Some conversions use integer division to recover image counts. These are correct only if the numerator is guaranteed to be an exact multiple of the group-grid dimension, including for negative values under Fortran truncation rules. Unit tests should exercise both positive and negative boundary images.",
            ),
        ],
    ),
    (
        "Interactions, matrices, density, and basis functions",
        [
            H("Localized basis and projector paths"),
            P(
                "PAO_grid_transform_module and blip_grid_transform_module now derive support-grid positions from lattice vectors. pseudo_tm_module and pseudopotential.module use general grid offsets in neutral-atom density, local pseudopotential, projector, and force/stress integrals. These changes are essential because a correct global cell with an orthogonal local grid mapping would silently integrate functions at the wrong Cartesian positions."
            ),
            H("Density construction"),
            P(
                "density_module updates multiple density accumulation paths to use vector-valued block and point positions. The changes cover support-function and PAO-related density evaluation, including force/stress-sensitive coordinate factors. The grid-point volume is determinant-based through dimens_module."
            ),
            H("Matrix images and restart state"),
            P(
                "S_matrix_module, UpdateInfo_module, UpdateMember_module, and store_matrix_module replace several scalar image translations. store_matrix_module additionally records lattice-related state for matrix reuse and compares cell changes. This is important for CG and MD, where reusing a matrix built for a geometrically different cell can corrupt forces or convergence."
            ),
            H("DFT-D2"),
            P(
                "DFT_D2_module delegates periodic displacement handling to the new MIC infrastructure instead of independent length-based wrapping. This enables dispersion across skewed boundaries for ordinary cells. The general shortest-image caveat still applies, and a D2 finite-difference force check in a strongly skewed cell remains required."
            ),
            H("Constraints"),
            P(
                "constraint_module replaces component-wise x/y/z wrapping in SHAKE and water-SHAKE with mic_coords. This eliminates an explicit orthorhombic assumption and also removes a latent branch typo in the old component handling. Constraint energies and multipliers should nevertheless be regression-tested across boundaries."
            ),
        ],
    ),
    (
        "Forces and the full stress tensor",
        [
            H("Why zero forces were observed"),
            P(
                "The immediate zero-force symptom in the early relaxation inputs was primarily caused by atomic movement flags set to F F F. CONQUEST intentionally zeroes constrained force components before reporting and optimization. Correct relaxation fixtures use T T T for movable carbon atoms. This input error was distinct from the deeper non-orthogonal force and stress work."
            ),
            H("Off-diagonal stress propagation"),
            P(
                "force_module expands many loops from diagonal-only contributions to all requested (dir1,dir2) components when AtomMove.FullStress is active. The affected terms include kinetic and overlap/Pulay stresses, support-function Pulay terms, nonlocal pseudopotential terms, local/Hartree/XC-related contributions, atomic stress accumulation, and final total-stress assembly."
            ),
            P(
                "The total tensor is assembled from the existing physical contributions and is printed as a full matrix where requested. The MD barostat path was adjusted to accept the off-diagonal static tensor instead of assuming only three normal components. A symmetric physical stress tensor should be checked explicitly after numerical assembly; the current calculations reported symmetric behavior within numerical noise."
            ),
            H("Coordinate factors in stress"),
            P(
                "Several force and stress integrals previously multiplied by Cartesian positions generated from scalar x/y/z grid spacing. They now use the vector-derived physical grid position. This is a fundamental correction: off-diagonal stress such as sigma_xy is a first moment coupling an x-like derivative or force to a y-like coordinate, and it cannot be correct if the cell shear is omitted from the grid geometry."
            ),
            H("Required validation"),
            B(
                "Central finite-difference each of the six independent strain components and compare dE/d epsilon to the analytic stress convention.",
                "Central finite-difference representative atomic displacements in x, y, and z for both skewed graphite and monoclinic HfO2.",
                "Check translational invariance: the vector sum of forces must be near zero.",
                "Check rotational/symmetry expectations where applicable and stress symmetry sigma_ij = sigma_ji.",
                "Repeat with D2 on/off, PAO and blip support representations, diagonalization and linear scaling, spin polarization, and multiple MPI decompositions.",
            ),
        ],
    ),
    (
        "Variable-cell conjugate-gradient relaxation",
        [
            H("Affine deformation fix"),
            P(
                "The earlier cell-update path overwrote the inverse lattice before using it to recover atomic fractional coordinates. As a result, changing the cell could leave atoms at effectively unchanged Cartesian coordinates instead of applying an affine deformation. update_cell_dims now snapshots the old direct and inverse lattice, computes fractional coordinates with the old inverse, updates the cell, and maps the same fractional coordinates through the new direct lattice."
            ),
            C(
                "old_A     = A\n"
                "old_A_inv = inverse(A)\n"
                "s_i       = old_A_inv r_i\n"
                "A         = A_new\n"
                "r_i       = A s_i"
            ),
            H("Reciprocal and density updates"),
            P(
                "The same operation preserves fractional reciprocal coordinates for k-points and FFT vectors, reconstructing them with the new A^{-T}. Density is scaled by old_volume/new_volume to preserve integrated charge, grid-point volume and Hartree factors are updated, and the reciprocal lattice cache is refreshed."
            ),
            H("Six-component lattice line search"),
            P(
                "The backtrack_linemin_lattice path forms a symmetric search tensor D from the effective stress and applies A_trial = (I + alpha D) A0. This uses all six physical strain components without privileging an upper-triangular orientation. External pressure is included on the diagonal. Trial steps reject non-positive volumes and use enthalpy decrease and directional-derivative logic. If no numerically resolvable downhill step remains at small residual stress, the cell is restored rather than terminating destructively."
            ),
            H("Observed graphite behavior"),
            P(
                "The graphite cell-only method converges using the symmetric-strain update at fixed fractional atomic coordinates. In that trajectory, maximum stress falls from 22.3003 GPa to 0.011651 GPa in 19 accepted steps. The maintained coupled runner selects OptCellMethod 2; it independently converged both atoms and cell in six outer cycles, ending at 0.00019971 Ha/bohr maximum force and 0.043113 GPa maximum stress."
            ),
            H("Observed HfO2 behavior"),
            Q(
                "Unresolved failure",
                "The HfO2 full-lattice smoke run reduced enthalpy and stress for several iterations, then emitted 'Failed to reduce enthalpy in full-lattice backtracking'. This means the optimizer is not yet robust for the intended monoclinic oxide case. The report therefore treats HfO2 relaxation as pending, consistent with the decision to defer its physics analysis.",
            ),
            H("Legacy optimizer overlap"),
            P(
                "move_atoms.module and control.f90 still contain older three-length optimization methods alongside the new full-lattice route. Several of those paths compute volume as a product of cell_vec_len or rescale Cartesian axes independently. A production implementation should either route all general-cell operation through update_lattice_vectors or explicitly prohibit non-orthogonal cells in legacy methods."
            ),
        ],
    ),
    (
        "Specialized physics paths and current gaps",
        [
            H("Ion electrostatics and Ewald"),
            Q(
                "PR blocker",
                "ion_electrostatic_module now passes the complete direct lattice to the existing general Ewald routine rather than reconstructing a diagonal cell from vector lengths. A unimodularly equivalent primitive-Si representation produced identical printed real-space Ewald energy and a total DFT difference of 4e-6 Ha, consistent with grid discretization. This is a static input-basis check, not completion of variable-cell Ewald: cached real/reciprocal lists, forces, and stresses still require explicit rebuild and finite-difference validation.",
            ),
            H("Polarization"),
            Q(
                "PR blocker",
                "polarisation_module computes volume as the product of vector lengths and obtains fractional ionic coordinates by dividing Cartesian x/y/z by the corresponding length. Both operations are wrong for a skewed cell. The correction is determinant volume plus matmul(lat_vec_inv,r). Berry-phase direction handling also needs a reciprocal-lattice audit.",
            ),
            H("vdW-DFT"),
            Q(
                "PR blocker when vdW-DFT is claimed",
                "vdWDFT_module estimates reciprocal cutoffs from vector lengths and sets d3k to the inverse product of lengths. The determinant must be used for reciprocal volume, and anisotropic cutoff selection should be based on reciprocal lattice vectors, not only direct-vector norms.",
            ),
            H("Molecular dynamics and barostats"),
            P(
                "md_control_module accepts more general static stress information but its variable-cell propagation remains strongly diagonal: reference and current lattice values are assigned through diagonal entries and several rescalings operate independently by length. NVE on a fixed skewed cell may work through the shared geometry, but variable-cell NPT/MTTK behavior is not established."
            ),
            H("Polar and response properties"),
            P(
                "Any method that interprets Cartesian components as fractional directions, constructs reciprocal grids from three lengths, or serializes a cell as only three numbers must be audited. This includes polarization, response functions, restart compatibility, and external interfaces. A repository-wide search still finds legacy length names in a small set of source files and several product-of-length formulas in active routines."
            ),
            H("Minimum-image rigor"),
            P(
                "For ordinary graphite and the present HfO2 cell, component-wise fractional rounding is usually adequate. To claim arbitrary triclinic support, the MIC must be exact for unreduced cells. A compact robust implementation can test translations n + delta for n in {-1,0,1}^3 around the rounded candidate and choose the minimum Cartesian norm; more advanced reduced-lattice approaches may be preferable for performance-critical loops."
            ),
        ],
    ),
    (
        "EXX and non-feature diff noise",
        [
            H("exx_kernel_default.f90"),
            P(
                "The raw diff reports 1,917 deleted and 1,917 inserted lines, suggesting a complete replacement. A whitespace-insensitive comparison returns no semantic difference. The EXX file is therefore not part of the present non-orthogonal implementation despite the accidental commit message describing threading and deduplication. Keeping this replacement would make code review dramatically harder and create needless merge conflicts."
            ),
            H("Other low-value churn"),
            P(
                "The three XC implementations contained comment-only substitutions and the EXX file was whitespace-only churn. Those changes were dropped from the curated checkpoint. Empty USE lists and diff whitespace introduced by the conversion were also cleaned so reviewers can focus on geometry and physics."
            ),
            H("Debug output"),
            Q(
                "Removed",
                "The accidental unconditional DEBUG: BEGIN main.f90 write and flush have been removed from the checkpoint. Historical generated output containing that line is not tracked.",
            ),
            H("Recommended commit split"),
            B(
                "Commit 1: lattice data model, inverse/determinant helpers, input/output conventions, and reciprocal transforms.",
                "Commit 2: real-space grid geometry and FFT reciprocal construction.",
                "Commit 3: partition, cover, image-translation, and MIC conversions.",
                "Commit 4: force and full-stress tensor propagation with finite-difference tests.",
                "Commit 5: affine cell updates and six-component cell optimizer.",
                "Commit 6: compact tracked examples and evidence; keep HfO2 explicitly pending until it satisfies its acceptance contract.",
                "Separate follow-up commits for variable-cell Ewald caches and derivatives, polarization, vdW-DFT, and variable-cell MD after their own validation.",
            ),
        ],
    ),
    (
        "Validation evidence obtained so far",
        [
            H("Build"),
            P(
                "make -C src -j2 completed with the configured macOS system file. The executable used for physics runs is the locally built bin/Conquest. Generated build files and binaries are deliberately excluded from the checkpoint. A clean build on CI compilers remains necessary."
            ),
            H("Graphite and graphene electronic structure"),
            T(
                ["System", "SCF mesh", "SCF convergence", "Band path", "K direct gap", "pDOS integral"],
                [
                    ["AB graphite", "15 x 15 x 5", "9 iterations; 5.72e-10 residual", "G-M-K-G-A; 197 points", "0.051745 meV", "16.000 e"],
                    ["Graphene", "21 x 21 x 1", "7 iterations; 8.87e-9 residual", "G-M-K-G; 178 points", "0.492624 meV", "8.000 e"],
                ],
                [2.4 * cm, 2.2 * cm, 3.4 * cm, 3.1 * cm, 2.2 * cm, 2.0 * cm],
            ),
            P(
                "The nearly zero K direct gaps are numerical residuals and demonstrate that the corrected reciprocal path and converged-density band workflow recover the expected Dirac-like crossings. The graphite DOS remains small but finite near the Fermi energy, while graphene shows the expected suppressed DOS around the crossing after Gaussian broadening. Carbon s, p, and d projections are resolved from PostProcessCQ."
            ),
            F("assets/graphite_band_pdos.png", "AB graphite band structure and atom-summed l-resolved projected DOS."),
            F("assets/graphene_band_pdos.png", "Graphene band structure and atom-summed l-resolved projected DOS."),
            H("Force and stress observations"),
            P(
                "For the corrected graphite relaxation fixtures, movable atom flags yield nonzero forces and full stress output includes shear components. The maintained full-cell runner asserts geometry convergence. Compact numerical evidence is tracked in the test reference directory; broader atomic finite-difference assertions remain future work."
            ),
            H("Test runner state"),
            P(
                "The extended examples 010-013 carry local README validation contracts and compact reference artifacts. They are not prematurely wired into the legacy sample-output pytest harness: test 011 is explicitly pending, while tests 010, 012, and 013 use staged workflows with their own convergence and physics checks. Future commits can promote compact quantities into automated assertions after tolerances are agreed."
            ),
            H("Finite differences"),
            P(
                "Primitive Si now provides a publication-quality six-strain driver with machine-readable analytic-versus-numerical derivatives, explicit stress convention, units, and error metrics. The same pattern should next be applied to graphite with D2 and to monoclinic HfO2 with explicit ionic Ewald."
            ),
        ],
    ),
    (
        "Tracked per-file implementation inventory",
        [
            P(
                "The following inventory covers every tracked file differing from the Bowler baseline. Descriptions distinguish substantive general-cell work from mechanical substitutions and review noise."
            ),
            T(
                ["File", "Role in the change", "Audit status"],
                [
                    ["src/global_module.f90", "Adds lattice matrix/inverse, determinant state, wrapping, MIC, reciprocal transforms, and grid-position helpers.", "Core; test independently."],
                    ["src/dimens_module.f90", "Replaces scalar supercell with matrices; determinant volume; norm-based grid estimates.", "Core."],
                    ["src/initial_read_module.f90", "General k-point transforms and norm-based grid reporting.", "Core; output round-trip test."],
                    ["src/io_module.f90", "Reads/writes off-diagonal cells, coordinate transforms, stress metadata.", "Core; one product-volume defect remains."],
                    ["src/control.f90", "Initializes lattice state; integrates full stress and full-lattice cell CG.", "Core; large and needs decomposition."],
                    ["src/move_atoms.module.f90", "Affine cell updates, reciprocal/density refresh, full-lattice line search, wrapping conversions.", "Core; legacy paths remain."],
                    ["src/force_module.f90", "Extends stress contributions and coordinate factors to off-diagonal components.", "Core; finite-difference validation required."],
                    ["src/set_blipgrid_module.f90", "Parallelotope AABB, vector grid spans, skew-cell block bounds.", "Core; high-risk indexing."],
                    ["src/sfc_partitions_module.f90", "cell_min offsets and skew-cell Hilbert mapping.", "Core; negative-boundary tests."],
                    ["src/cover_module.f90", "Integer image translations through full lattice vectors.", "Core; boundary arithmetic tests."],
                    ["src/primary_module.f90", "Vector-valued group-cell displacement and primary-set translations.", "Core."],
                    ["src/atom_dispenser_module.f90", "General cell geometry in atom-to-grid distribution.", "Core; inspect duplicate initialization."],
                    ["src/PAO_grid_transform_module.f90", "Lattice-based PAO grid origins and point offsets.", "Substantive."],
                    ["src/blip_grid_transform_module.f90", "Lattice-based blip grid origins and point offsets.", "Substantive."],
                    ["src/density_module.f90", "General physical positions throughout density accumulation.", "Substantive."],
                    ["src/pseudo_tm_module.f90", "General grid geometry in pseudo/neutral-atom integrations.", "Substantive."],
                    ["src/pseudopotential.module.f90", "General grid geometry in pseudopotential/projector paths.", "Substantive."],
                    ["src/S_matrix_module.f90", "Periodic translations and overlap geometry use lattice vectors.", "Substantive."],
                    ["src/UpdateInfo_module.f90", "Image and matrix-neighbor metadata updated for vector translations.", "Substantive; empty USE cleanup."],
                    ["src/UpdateMember_module.f90", "Boundary membership/image shifts use integer lattice translations.", "Substantive."],
                    ["src/store_matrix_module.f90", "Persists and compares new cell-related state for reuse/restart.", "Substantive; restart compatibility test."],
                    ["src/fft_module.f90", "General reciprocal-vector construction and norm-based grid quantities.", "Substantive."],
                    ["src/constraint_module.f90", "SHAKE periodic wrapping delegated to MIC helper.", "Substantive; MIC caveat."],
                    ["src/DFT_D2_module.f90", "Dispersion displacement uses general MIC/length state.", "Substantive; FD test."],
                    ["src/exx_module.f90", "Small scalar-length compatibility conversion.", "Partial; EXX physics not established."],
                    ["src/exx_kernel_default.f90", "Whole-file whitespace-only replacement.", "Drop from PR."],
                    ["src/ion_electrostatic_module.f90", "Complete lattice passed into static general Ewald setup.", "Static basis check passes; variable-cell caches and derivatives remain."],
                    ["src/polarisation_module.f90", "Mechanical length substitution in volume/fractional coordinates.", "Incorrect for skew cells."],
                    ["src/vdWDFT_module.f90", "Length-based cutoff/volume substitutions.", "Incomplete for skew cells."],
                    ["src/md_control_module.f90", "Moves some state to cell_vec_len; accepts fuller stress.", "Transitional; variable-cell MD diagonal."],
                    ["src/md_misc_module.f90", "Scalar cell names migrated to length array.", "Compatibility only."],
                    ["src/md_model_module.f90", "Scalar cell names migrated to length array.", "Compatibility only."],
                    ["src/XLBOMD_module.f90", "Scalar reference migrated to length array.", "Compatibility only."],
                    ["src/initialisation_module.f90", "Synchronizes vector-based cell state during initialization.", "Keeps lattice, inverse, reciprocal, lengths, and determinant consistent."],
                    ["src/XC_CQ_module.f90", "Mostly comments; gradient already uses reciprocal vectors.", "Review noise."],
                    ["src/XC_LibXC_v4_module.f90", "Mostly comments; gradient already uses reciprocal vectors.", "Review noise."],
                    ["src/XC_LibXC_v5_module.f90", "Mostly comments; gradient already uses reciprocal vectors.", "Review noise."],
                    ["src/main.f90", "Removes the accidental unconditional debug write.", "Cleaned in checkpoint."],
                    ["testsuite tests 010-013", "Adds documented extended workflows and compact reference evidence.", "010/012/013 validated; 011 explicitly pending."],
                ],
                [4.4 * cm, 8.0 * cm, 3.1 * cm],
            ),
        ],
    ),
    (
        "Risk register and pull-request acceptance criteria",
        [
            T(
                ["Priority", "Risk", "Evidence", "Acceptance criterion"],
                [
                    ["P0", "Variable-cell Ewald lifecycle incomplete", "Static setup now receives lat_vec; cached lists/derivatives are not yet fully accepted.", "Rebuild after cell changes and match force/stress finite differences for skew ionic crystals."],
                    ["P0", "Polarization formulas are orthorhombic", "Length-product volume and component division.", "Use determinant/inverse; validate Berry-phase polarization."],
                    ["P0", "Full-lattice HfO2 line search fails", "Backtracking failure in relax_smoke.", "Convergent enthalpy/stress trajectory with reproducible endpoint."],
                    ["P0", "Tests are not committed", "test_010/test_011 directories untracked.", "Small deterministic fixtures run in CI on 1 and 2 ranks."],
                    ["P1", "MIC can miss shortest triclinic image", "Independent fractional rounding.", "Reduced-cell guarantee or neighbor-image shortest-vector search."],
                    ["P1", "Legacy cell paths use product volume", "Active formulas in move_atoms/polarization/vdW/io.", "All claimed general-cell paths use det(A)."],
                    ["P1", "Variable-cell MD remains diagonal", "md_control diagonal lattice updates.", "Either implement full matrix propagation or reject skew variable-cell MD."],
                    ["P1", "Stress coverage incomplete across physics modes", "Primitive Si now passes all six strain checks.", "Repeat six strains for ionic Ewald, D2, spin, and other specialist paths."],
                    ["P2", "Review-obscuring diff noise", "EXX whitespace-only replacement and trailing spaces.", "Whitespace-clean focused diff."],
                    ["P2", "Unconditional debug output", "main.f90 write/flush.", "Remove and verify clean stderr."],
                    ["P2", "Generated artifacts dominate test tree", "WF, density, matrices, logs, images.", "Curate inputs/reference scalars; add ignore rules."],
                ],
                [1.2 * cm, 4.1 * cm, 4.6 * cm, 5.6 * cm],
            ),
            H("Minimum physics matrix before PR"),
            B(
                "Orthogonal-cell regression: energies, forces, stress, band structure, and restart results unchanged within existing tolerances.",
                "Hexagonal graphite: static energy, full stress, atomic finite differences, six strain finite differences, D2 on/off, bands and DOS.",
                "Graphene slab: vacuum-direction stability, K crossing, zero-force symmetry, and in-plane strain derivatives.",
                "Monoclinic HfO2: ionic Ewald correctness, nonzero forces on movable atoms, full-stress finite differences, and successful coupled atom/cell relaxation.",
                "A deliberately strongly skewed triclinic toy cell: exact MIC compared with brute-force image enumeration.",
                "MPI reproducibility on one and two ranks, plus at least one larger decomposition in CI or cluster validation.",
                "PAO and blip basis paths, diagonalization and linear-scaling paths, and restart/matrix-reuse behavior after a cell change.",
            ),
            H("Engineering acceptance"),
            B(
                "Clean build from scratch on GNU and Intel/LLVM-class Fortran compilers.",
                "No debug writes, empty USE clauses, duplicate assignments, or diff whitespace warnings.",
                "Documented matrix orientation and reciprocal convention at every external interface.",
                "One authoritative cell-update transaction, or explicit guards on legacy orthogonal-only routes.",
                "Compact commit history aligned with architectural layers.",
                "User documentation with supported/unsupported feature matrix and example inputs.",
            ),
        ],
    ),
    (
        "Proposed completion roadmap",
        [
            H("Phase 1 - Curate and lock the core"),
            P(
                "Remove unrelated EXX formatting, debug output, scratch scripts, and generated files. Commit the matrix convention and core helpers first. Add unit tests for inverse/determinant, direct/reciprocal round trips, wrapping, grid origins, and brute-force MIC comparisons. This creates a trustworthy geometric foundation before more physics is evaluated."
            ),
            H("Phase 2 - Static DFT path"),
            P(
                "Complete real-space grid, FFT, matrix-image, local/nonlocal pseudopotential, Hartree, XC, and D2 coverage. Complete the variable-cell Ewald lifecycle and run force/stress finite differences for graphite and HfO2. Static energies, forces, and all six stress components remain the first pull-request gate."
            ),
            H("Phase 3 - Relaxation"),
            P(
                "Consolidate cell updates around one affine matrix routine. Diagnose HfO2 line-search gradients using finite-difference enthalpy directional derivatives. Add safeguards for determinant, condition number, maximum strain, and basis/grid discontinuities. Demonstrate repeatable convergence from multiple initial strains."
            ),
            H("Phase 4 - Specialist features"),
            P(
                "Repair and validate polarization, vdW-DFT, exact exchange, constraints, and variable-cell MD independently. If schedule requires, explicitly mark unsupported combinations instead of allowing silently wrong results."
            ),
            H("Phase 5 - Pull request"),
            P(
                "Rebase the curated feature branch onto the latest upstream develop, resolve interfaces without reintroducing scalar cell assumptions, run the complete validation matrix, and attach this report plus machine-readable test summaries to the PR. The remote develop correction should be coordinated separately because origin/develop already contains the accidental commit."
            ),
        ],
    ),
    (
        "Conclusions",
        [
            P(
                "The implementation changes the geometric foundation of CONQUEST from three orthogonal box lengths toward a coherent lattice-matrix model. That is a large and important advance. The most compelling results are the determinant/inverse infrastructure, correct reciprocal transforms, vector-derived grid geometry, skew-cell partition bounds, exact integer lattice translations, propagation of off-diagonal stress, affine preservation of fractional coordinates, and an orientation-independent symmetric-strain cell line search."
            ),
            P(
                "The corrected graphite and graphene electronic structures provide visible confirmation that the reciprocal and real-space paths can now work together for non-90-degree cells. The force/stress and relaxation diagnostics show that the code is no longer trapped at the previous zero-force/input state and that cell degrees of freedom produce meaningful responses."
            ),
            P(
                "The same audit also shows why a careful physics-confirmation stage is essential. General-cell support is a cross-cutting property: one stale Ewald cache or one product-of-length volume can invalidate an otherwise sophisticated calculation. The remaining issues are identifiable and tractable, and the feature branch provides the correct place to resolve them without contaminating develop."
            ),
            Q(
                "Final status",
                "Major progress: yes. Correct branch isolation: completed locally. Ready for pull request today: no. Ready for systematic physics completion and review: yes.",
            ),
        ],
    ),
    (
        "Appendix A - Reproduction commands and artifacts",
        [
            C(
                "# Build\n"
                "make -C src -j2\n\n"
                "# Graphite bands and pDOS (maximum two MPI ranks)\n"
                "NP=2 ./testsuite/test_010_graphite_monoclinic/run_graphite_hcp.sh\n\n"
                "# Graphene bands and pDOS\n"
                "NP=2 ./testsuite/test_010_graphite_monoclinic/run_graphene.sh\n\n"
                "# Compare all tracked work against Bowler baseline\n"
                "git diff --stat 34de2d610eec5fefce834cfd469b5f3354d5a9ef\n"
                "git diff --ignore-all-space --stat 34de2d610eec5fefce834cfd469b5f3354d5a9ef\n\n"
                "# Confirm branch pointers\n"
                "git rev-parse develop feature/general-nonorthogonal-cells origin/develop"
            ),
            T(
                ["Artifact", "Location"],
                [
                    ["Graphite combined image", "testsuite/test_010_graphite_monoclinic/reference/graphite_band_pdos.png"],
                    ["Graphene combined image", "testsuite/test_010_graphite_monoclinic/reference/graphene_band_pdos.png"],
                    ["Graphite band eigenvalues", "testsuite/test_010_graphite_monoclinic/band_pdos_results/graphite/bands/eigenvalues.dat"],
                    ["Graphite DOS/pDOS", "testsuite/test_010_graphite_monoclinic/band_pdos_results/graphite/pdos/"],
                    ["Graphene band eigenvalues", "testsuite/test_010_graphite_monoclinic/band_pdos_results/graphene/bands/eigenvalues.dat"],
                    ["Graphene DOS/pDOS", "testsuite/test_010_graphite_monoclinic/band_pdos_results/graphene/pdos/"],
                    ["Cell finite-difference diagnostics", "testsuite/test_010_graphite_monoclinic/diagnostics/cell_fd_base and cell_fd_step"],
                    ["Graphite validation summary", "testsuite/test_010_graphite_monoclinic/reference/summary.json"],
                    ["Primitive Si reference suite", "testsuite/test_012_bulk_Si_primitive_nonorthogonal/reference/"],
                    ["Rutile reference suite", "testsuite/test_013_rutile_TiO2_tetragonal/reference/"],
                ],
                [5.0 * cm, 10.5 * cm],
            ),
        ],
    ),
]


def latex_escape(text):
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def write_latex():
    lines = [
        r"\documentclass[10pt,a4paper]{report}",
        r"\usepackage[a4paper,margin=22mm]{geometry}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage{lmodern}",
        r"\usepackage{microtype}",
        r"\usepackage{amsmath,amssymb}",
        r"\usepackage{graphicx}",
        r"\usepackage{booktabs,longtable,tabularx,array}",
        r"\usepackage{xcolor}",
        r"\usepackage{listings}",
        r"\usepackage{enumitem}",
        r"\usepackage{fancyhdr}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\definecolor{cqblue}{HTML}{155E75}",
        r"\definecolor{cqred}{HTML}{9F1239}",
        r"\definecolor{cqgray}{HTML}{F3F4F6}",
        r"\lstset{basicstyle=\ttfamily\small,breaklines=true,frame=single,backgroundcolor=\color{cqgray}}",
        r"\pagestyle{fancy}\fancyhf{}\lhead{CONQUEST general-cell implementation audit}\rhead{\thepage}",
        r"\setlist[itemize]{leftmargin=6mm,itemsep=2pt,topsep=3pt}",
        r"\title{\Huge General Non-Orthogonal Cell Support in CONQUEST\\[5mm]\Large Engineering, Physics, and Pull-Request Readiness Report}",
        r"\author{Feature branch audit for Augustin Lu}",
            r"\date{29 July 2026}",
        r"\begin{document}",
        r"\maketitle",
        r"\begin{center}",
        r"\begin{tabular}{ll}",
        r"\toprule",
        rf"Baseline & \texttt{{{BASELINE}}}\\",
        rf"Feature head & \texttt{{{FEATURE_HEAD}}}\\",
        rf"Feature branch & \texttt{{{latex_escape(BRANCH)}}}\\",
        r"Status & Major progress; physics validation and cleanup still required\\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{center}",
        r"\clearpage",
        r"\tableofcontents",
        r"\clearpage",
    ]
    for title, blocks in SECTIONS:
        lines.append(r"\chapter{" + latex_escape(title) + "}")
        for block in blocks:
            kind = block[0]
            if kind == "p":
                lines.append(latex_escape(block[1]) + "\n")
            elif kind == "subheading":
                lines.append(r"\section{" + latex_escape(block[1]) + "}")
            elif kind == "bullets":
                lines.append(r"\begin{itemize}")
                lines.extend(r"\item " + latex_escape(item) for item in block[1])
                lines.append(r"\end{itemize}")
            elif kind == "code":
                lines.append(r"\begin{lstlisting}")
                lines.append(block[1])
                lines.append(r"\end{lstlisting}")
            elif kind == "callout":
                lines.append(r"\begin{center}\fcolorbox{cqred}{cqgray}{\begin{minipage}{0.91\textwidth}")
                lines.append(r"\textbf{" + latex_escape(block[1]) + r"}\par")
                lines.append(latex_escape(block[2]))
                lines.append(r"\end{minipage}}\end{center}")
            elif kind == "figure":
                lines.append(r"\begin{figure}[htbp]\centering")
                lines.append(r"\includegraphics[width=\textwidth]{" + latex_escape(block[1]) + "}")
                lines.append(r"\caption{" + latex_escape(block[2]) + "}")
                lines.append(r"\end{figure}")
            elif kind == "table":
                headers, rows = block[1], block[2]
                ncol = len(headers)
                colspec = "|".join([r"p{" + f"{0.93 / ncol:.3f}" + r"\textwidth}" for _ in headers])
                lines.append(r"\small\begin{longtable}{" + colspec + "}")
                lines.append(r"\toprule " + " & ".join(latex_escape(x) for x in headers) + r"\\ \midrule\endhead")
                for row in rows:
                    lines.append(" & ".join(latex_escape(str(x)) for x in row) + r"\\")
                lines.append(r"\bottomrule\end{longtable}\normalsize")
            elif kind == "pagebreak":
                lines.append(r"\clearpage")
    lines.extend(
        [
            r"\appendix",
            r"\chapter{Audit provenance}",
            r"This report was generated from the curated local checkpoint on 29 July 2026. It deliberately compares the implementation with David Bowler's baseline commit \texttt{34de2d61}; it does not treat the accidental feature commit as the baseline.",
            r"\end{document}",
        ]
    )
    TEX_PATH.write_text("\n".join(lines), encoding="utf-8")


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.4,
        leading=13.2,
        alignment=TA_JUSTIFY,
        spaceAfter=7,
        textColor=colors.HexColor("#1F2937"),
    )
)
styles.add(
    ParagraphStyle(
        name="ReportH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#155E75"),
        spaceBefore=8,
        spaceAfter=12,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        name="ReportH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#111827"),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        name="ReportBullet",
        parent=styles["ReportBody"],
        leftIndent=14,
        firstLineIndent=-8,
        bulletIndent=3,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="ReportCaption",
        parent=styles["BodyText"],
        fontName="Helvetica-Oblique",
        fontSize=8.2,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4B5563"),
        spaceBefore=3,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="CalloutTitle",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#9F1239"),
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="CalloutBody",
        parent=styles["ReportBody"],
        fontSize=9,
        leading=12.5,
        spaceAfter=0,
    )
)


class ReportDocTemplate(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=2.0 * cm,
            rightMargin=2.0 * cm,
            topMargin=1.9 * cm,
            bottomMargin=1.8 * cm,
            title="General Non-Orthogonal Cell Support in CONQUEST",
            author="Feature branch audit for Augustin Lu",
        )
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal")
        self.addPageTemplates(
            [
                PageTemplate(id="title", frames=[frame], onPage=self.title_page),
                PageTemplate(id="body", frames=[frame], onPage=self.body_page),
            ]
        )

    def title_page(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#155E75"))
        canvas.rect(0, A4[1] - 1.1 * cm, A4[0], 1.1 * cm, stroke=0, fill=1)
        canvas.restoreState()

    def body_page(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D1D5DB"))
        canvas.line(self.leftMargin, A4[1] - 1.2 * cm, A4[0] - self.rightMargin, A4[1] - 1.2 * cm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#4B5563"))
        canvas.drawString(self.leftMargin, A4[1] - 0.9 * cm, "CONQUEST general-cell implementation audit")
        canvas.drawRightString(A4[0] - self.rightMargin, 0.9 * cm, f"Page {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style = flowable.style.name
            if style == "ReportH1":
                self.canv.bookmarkPage(f"h1-{self.seq.nextf('h1')}")
                self.canv.addOutlineEntry(flowable.getPlainText(), f"h1-{self.seq.thisf('h1')}", level=0)
                self.notify("TOCEntry", (0, flowable.getPlainText(), self.page))
            elif style == "ReportH2":
                self.notify("TOCEntry", (1, flowable.getPlainText(), self.page))


def para(text, style="ReportBody"):
    return Paragraph(xml_escape(text), styles[style])


def make_table(headers, rows, widths=None):
    data = [[Paragraph(f"<b>{xml_escape(str(h))}</b>", styles["ReportBody"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(xml_escape(str(cell)), styles["ReportBody"]) for cell in row])
    table = LongTable(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCEFF3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]
        )
    )
    return table


def build_pdf():
    story = []
    story.append(Spacer(1, 2.0 * cm))
    story.append(
        Paragraph(
            "General Non-Orthogonal Cell Support<br/>in CONQUEST",
            ParagraphStyle(
                "TitleLarge",
                parent=styles["Title"],
                fontName="Helvetica-Bold",
                fontSize=27,
                leading=32,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#111827"),
                spaceAfter=16,
            ),
        )
    )
    story.append(
        Paragraph(
            "Engineering, Physics, and Pull-Request Readiness Report",
            ParagraphStyle(
                "Subtitle",
                parent=styles["Title"],
                fontName="Helvetica",
                fontSize=15,
                leading=20,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#155E75"),
                spaceAfter=28,
            ),
        )
    )
    title_rows = [
        ["Baseline", BASELINE],
        ["Feature head", FEATURE_HEAD],
        ["Feature branch", BRANCH],
        ["Audit date", "29 July 2026"],
        ["Status", "Validated foundation; bounded ionic and specialist follow-up required"],
    ]
    story.append(make_table(["Field", "Value"], title_rows, [3.2 * cm, 11.8 * cm]))
    story.append(Spacer(1, 0.8 * cm))
    story.append(
        para(
            "Prepared as a complete comparison against David Bowler's true develop baseline, not against the accidental feature commit.",
            "ReportCaption",
        )
    )
    story.append(NextPageTemplate("body"))
    story.append(PageBreak())
    story.append(Paragraph("Contents", styles["ReportH1"]))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(name="TOC1", fontName="Helvetica-Bold", fontSize=10, leading=14, leftIndent=0, firstLineIndent=0),
        ParagraphStyle(name="TOC2", fontName="Helvetica", fontSize=9, leading=12, leftIndent=14, firstLineIndent=0),
    ]
    story.append(toc)
    story.append(PageBreak())

    for title, blocks in SECTIONS:
        story.append(Paragraph(xml_escape(title), styles["ReportH1"]))
        for block in blocks:
            kind = block[0]
            if kind == "p":
                story.append(para(block[1]))
            elif kind == "subheading":
                story.append(Paragraph(xml_escape(block[1]), styles["ReportH2"]))
            elif kind == "bullets":
                for item in block[1]:
                    story.append(Paragraph("- " + xml_escape(item), styles["ReportBullet"]))
                story.append(Spacer(1, 3))
            elif kind == "code":
                story.append(
                    Preformatted(
                        block[1],
                        ParagraphStyle(
                            "CodeBlock",
                            fontName="Courier",
                            fontSize=7.7,
                            leading=10,
                            leftIndent=8,
                            rightIndent=8,
                            borderColor=colors.HexColor("#CBD5E1"),
                            borderWidth=0.5,
                            borderPadding=7,
                            backColor=colors.HexColor("#F3F4F6"),
                            spaceBefore=4,
                            spaceAfter=9,
                        ),
                    )
                )
            elif kind == "callout":
                callout = Table(
                    [[Paragraph(xml_escape(block[1]), styles["CalloutTitle"])], [para(block[2], "CalloutBody")]],
                    colWidths=[15.5 * cm],
                )
                callout.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7ED")),
                            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#C2410C")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 8),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ]
                    )
                )
                story.extend([callout, Spacer(1, 8)])
            elif kind == "table":
                story.append(make_table(block[1], block[2], block[3]))
                story.append(Spacer(1, 8))
            elif kind == "figure":
                image_path = OUT / block[1]
                img = Image(str(image_path))
                available_w = 15.5 * cm
                available_h = 10.0 * cm
                scale = min(available_w / img.imageWidth, available_h / img.imageHeight)
                img.drawWidth = img.imageWidth * scale
                img.drawHeight = img.imageHeight * scale
                img.hAlign = "CENTER"
                story.append(img)
                story.append(para(block[2], "ReportCaption"))
            elif kind == "pagebreak":
                story.append(PageBreak())

    doc = ReportDocTemplate(str(PDF_PATH))
    doc.multiBuild(story)


if __name__ == "__main__":
    write_latex()
    build_pdf()
    print(TEX_PATH)
    print(PDF_PATH)
