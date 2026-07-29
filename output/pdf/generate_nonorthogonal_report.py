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
FEATURE_HEAD = "1ba828f4 (clean ancestry checkpoint)"
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
                "The supported general-cell implementation is complete for the audited scope. Direct and reciprocal geometry, real-space grids, exact periodic images, Ewald electrostatics, forces, all six stress components, method-2 atom/cell relaxation, polarization, vdW-DFT normalization, extended-XYZ output, and variable-cell MD bookkeeping now use a full lattice formulation. Tests 010 through 019 provide material and source-level evidence from hexagonal, tetragonal, primitive FCC, monoclinic, and deliberately unreduced triclinic cells. Legacy OptCellMethod 3 is intentionally guarded as orthorhombic-only.",
            ),
            P(
                "The comparison baseline throughout this report is David Bowler's merge commit 34de2d61, dated 2026-07-09, not the accidental develop-branch commit 7100d69d. The clean feature history contains ten focused commits and differs from the baseline in 177 tracked files: 34 source/build files, three documentation files, five report files, and 135 test files. The large insertion count is dominated by ion files and compact reference evidence; the semantic source changes are inventoried module by module below."
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
            H("Boundaries of the completion claim"),
            B(
                "OptCellMethod 2 is the supported atom-plus-cell CG route for skew cells. Legacy method 3 is rejected explicitly because its grid and cell parameterization remains orthorhombic.",
                "The NPT test validates one-step geometry, determinant volume, reciprocal/density rescaling, and preservation of skew shape. Long-trajectory thermodynamic sampling is a separate general MD validation topic.",
                "The exact MIC is geometrically general, but its finite search is more expensive than component rounding for severely unreduced cells.",
                "Scalar-relativistic material examples do not establish spin-orbit accuracy, quasiparticle gaps, or every exchange-correlation/basis combination.",
                "The macOS-only legacy four-rank PBE0/GTO test-005 failure reproduces at Bowler's untouched baseline and is explicitly outside this feature's scope.",
            ),
            H("Recommended release claim"),
            P(
                "For the pull request, describe this work as general non-orthogonal cell support for the validated static DFT, force/stress, method-2 relaxation, electronic post-processing, polarization, vdW-DFT normalization, and variable-cell MD geometry paths. State explicitly that method 3 remains orthorhombic-only and that specialist combinations not represented by tests 010-019 retain their normal feature-specific validation requirements."
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
                "Central energy derivatives for xx, yy, zz, xy, xz, and yz strains were compared with the analytic stress tensor in a deliberately distorted cell. The final two-rank rerun gives a maximum absolute error of 0.0548 GPa and RMS error of 0.0360 GPa. The analytic tensor is exactly symmetric at printed precision."
            ),
            H("Rutile TiO2"),
            P(
                "Rutile is anisotropic but right-angled, so it checks non-cubic regressions rather than non-90-degree geometry directly. Fixed-cell relaxation moves oxygen u from 0.312 to 0.3052583 and lowers the maximum force from 0.0137804 to 0.00015348 Ha/bohr. The LDA path gap is 1.7040 eV, with O-p valence and Ti-d conduction character. The SCF has 48 valence electrons; the chosen DOS window contains 32 because 16 Ti semicore electrons lie below it."
            ),
            H("Monoclinic HfO2"),
            Q(
                "Ionic monoclinic gate passed",
                "The 12-atom baddeleyite HfO2 test now rebuilds the complete Ewald state after every trial lattice, validates a representative Hf force against a central finite difference, validates all six isolated ion-ion and total PBE stress components, performs coupled method-2 atom/cell cycles, and compares determinant-one equivalent cells on one and two MPI ranks. The maximum isolated Ewald stress error is 0.00155 GPa; the maximum total-stress error is 0.04825 GPa.",
            ),
            H("Bulk 2H-MoS2"),
            P(
                "The six-atom P6_3/mmc test exercises a 120-degree layered transition-metal compound. Internal relaxation moves sulfur z from 0.615000 to 0.62118869 and reduces maximum force from 0.02736402 to 0.00019569 Ha/bohr. The scalar-PBE path is indirect with a 0.88044 eV gap, and the low conduction manifold has the expected dominant Mo-d character."
            ),
            H("Monoclinic ZrO2"),
            P(
                "A second 12-atom P21/c ionic oxide checks that HfO2 is not a one-material success. Fixed-cell relaxation reaches 0.00039986 Ha/a0 maximum force, SeeK-path recovers space group 14, the scalar-PBE path gap is 3.37893 eV, and pDOS shows O-p upper valence with Zr-d low conduction character."
            ),
            H("Specialist equivalent-cell gates"),
            P(
                "Primitive-Si polarization quanta agree to 2.05e-14 e/Bohr2 across determinant-one bases, transformed coefficients agree modulo a quantum to 9.69e-6, and complete extended-XYZ lattice/stress fields serialize to 4.96e-9 Angstrom and 7.93e-7 GPa. Equivalent graphene bases whose vector-length products differ by 1.732 retain vdW and corrected-energy agreement within 3.15e-4 Ha."
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
                    ["Clean foundation", "547babc0", "Foundation tree reconstructed directly on Bowler's baseline."],
                    ["Feature checkpoint", "1ba828f4", "Ten focused commits; accidental commit is not an ancestor."],
                    ["Safety branch", "backup/nonorthogonal-before-ancestry-cleanup-20260729", "Preserves the pre-rewrite tested history."],
                    ["Local develop", "34de2d61", "Restored to Bowler's baseline."],
                    ["origin/develop", "7100d69d", "Not force-updated by this work; remote correction still requires an explicit decision."],
                ],
                [3.1 * cm, 3.0 * cm, 9.4 * cm],
            ),
            C(
                "34de2d61  develop (Bowler baseline)\n"
                "    |\\\n"
                "    | +-- 7100d69d  origin/develop (accidental line)\n"
                "    |\n"
                "    +-- 547babc0  clean general-cell foundation\n"
                "          +-- ... nine focused commits ...\n"
                "                 +-- 1ba828f4  feature checkpoint"
            ),
            P(
                "The repair is deliberately recoverable. A safety branch preserves the original tested chain. A new foundation commit uses the exact tested ba2c9fe9 tree but names 34de2d61 as its parent; the nine later focused commits were replayed without conflict. Tree equivalence against the safety branch was verified with git diff --quiet. The accidental 7100d69d is not an ancestor of the clean feature branch, while Bowler's 34de2d61 is."
            ),
            H("Initial audit scope"),
            T(
                ["Layer", "Files", "Raw change", "Interpretation"],
                [
                    ["Source/build", "34", "33 Fortran modules plus Makefile", "General lattice, physics, relaxation, output, and MD."],
                    ["Documentation", "3", "User/reference manuals", "Supported method-2 path and method-3 guard documented."],
                    ["Tests", "135", "Tests 010-019 and reference evidence", "Materials, finite differences, invariance, MIC, specialist paths."],
                    ["Report", "5", "Generator, LaTeX, PDF, two figures", "Auditable implementation and validation narrative."],
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
                "General wrapping is performed by converting to fractional coordinates, subtracting floor(s) for [0,1) wrapping, and transforming back. Minimum-image displacements begin with the rounded fractional candidate, then derive a finite integer search bound from the inverse-lattice row norms and inspect every translation that can still be shorter. This returns the exact Euclidean nearest image even for strongly skewed and determinant-one unreduced bases."
            ),
            Q(
                "Exactness and cost",
                "Test 016 includes a 36.9-degree cell where independent fractional rounding is demonstrably wrong, plus an orthogonal lattice represented by a large unimodular shear. The production routine agrees with exhaustive enumeration. The bounded search is intentionally correctness-first; highly unreduced cells may benefit from lattice reduction as a future optimization.",
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
                "Maintained invariant",
                "Supported cell-changing paths update A, A^{-1}, A^{-T}, vector norms, determinant volume, grid-point volume, k-points, FFT reciprocal vectors, charge-density normalization, atom coordinates, Ewald state, and cached partition geometry as one coordinated operation. Method-2 relaxation and variable-cell MD tests exercise this invariant; method 3 is rejected for skew cells.",
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
            H("General-cell metadata"),
            P(
                "Extended XYZ now writes all nine lattice components and converts stress with determinant volume. Test 017 parses the serialized metadata and obtains maximum lattice and stress errors of 4.96e-9 Angstrom and 7.93e-7 GPa. Human-readable volume and stress paths use the central determinant state rather than the product of vector lengths."
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
            H("Validation status"),
            B(
                "Primitive Si passes central energy derivatives for all six independent strain components with 0.0548 GPa maximum error in the final rerun.",
                "Monoclinic HfO2 passes all six explicit-Ewald stress derivatives below 0.01 GPa and total PBE stress derivatives below 0.10 GPa.",
                "A representative Hf x force agrees with the full-force finite-difference harness to 3.75e-5 Ha/a0.",
                "Equivalent HfO2 lattice bases reproduce the printed Ewald energy exactly and one-/two-rank force and stress output identically.",
                "The analytic stress tensors are symmetric at printed precision in the six-strain gates.",
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
                "Resolved line-search defect",
                "The apparent uphill HfO2 step was traced to a stale volume-dependent core-correction energy after trial lattice changes. Recomputing that scalar with the rebuilt pseudopotential/Ewald state restored agreement with cold starts. The maintained two-cycle run accepts six cell steps, rebuilds Ewald 24 times, lowers energy from -358.70465487 to -358.70841529 Ha in the first cell cycle, and reduces maximum stress from 8.2732 to 0.0687 GPa.",
            ),
            H("Legacy optimizer overlap"),
            P(
                "CONQUEST retains older three-length optimization code for compatibility. General skew-cell atom-plus-cell relaxation is explicitly routed through OptCellMethod 2 with FullStress and the backtracking line minimizer. OptCellMethod 3 now aborts early on a skew lattice with a diagnostic directing users to method 2; test 019 enforces the guard."
            ),
        ],
    ),
    (
        "Specialized physics paths",
        [
            H("Ion electrostatics and Ewald"),
            Q(
                "Validated",
                "ion_electrostatic_module passes the complete lattice into Ewald setup and rebuilds cached real/reciprocal state after trial cell changes. Test 011 validates a representative force, all six isolated Ewald stress derivatives, all six total-stress derivatives, method-2 variable-cell execution, determinant-one basis invariance, and one-/two-rank reproducibility.",
            ),
            H("Polarization"),
            Q(
                "Validated geometry path",
                "polarisation_module uses determinant volume and the full inverse lattice for ionic fractional coordinates; S_matrix_module applies Resta phases through the same Cartesian-to-fractional transform. Test 017 checks polarization quanta and integer-basis covariance between equivalent primitive-Si cells.",
            ),
            H("vdW-DFT"),
            Q(
                "Validated normalization",
                "vdWDFT_module normalizes reciprocal integration with 1/abs(det(A)). Test 018 uses equivalent graphene bases whose vector-length products differ by sqrt(3) while their determinant is identical; the vdW correction and corrected energy remain within 2e-3 Ha finite-grid tolerances.",
            ),
            H("Molecular dynamics and barostats"),
            P(
                "md_control_module initializes from the full lattice, uses determinant volume, preserves every off-diagonal element under isotropic Parrinello-Rahman scaling, and applies xyz Cartesian strains to complete lattice rows. The cell update transforms k and FFT reciprocal vectors covariantly and rescales density by the determinant ratio. Test 019 validates one NPT step for volume and xyz constraints."
            ),
            H("Polar and response properties"),
            P(
                "The audit distinguished legitimate vector-length uses, such as reporting and grid-count estimates, from operations requiring the full matrix or determinant. Polarization and extended-XYZ metadata now have direct equivalent-cell tests. Other response methods inherit the corrected reciprocal vectors but remain subject to their ordinary feature-specific regression requirements."
            ),
            H("Minimum-image rigor"),
            P(
                "global_module now implements a bounded exact closest-image search rather than relying on component-wise rounding or a fixed {-1,0,1} cube. Test 016 compares it with exhaustive enumeration for a strongly skewed cell and a severely unreduced determinant-one representation."
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
            H("Implemented commit sequence"),
            B(
                "547babc0: general non-orthogonal cell foundation on Bowler's true baseline.",
                "eb9c1052: rebuild ionic Ewald state for variable cells.",
                "52209e4f: full stress and variable-cell energy consistency.",
                "e66efc92: bulk 2H-MoS2 validation.",
                "c3e1bca5: equivalent-cell and MPI invariance gate.",
                "ab91af2e: exact triclinic minimum images.",
                "6cc7e6dd: monoclinic ZrO2 bands and pDOS.",
                "22f3f822: polarization, vdW-DFT, and extended-XYZ geometry.",
                "cf511b23: full-lattice variable-cell MD bookkeeping and method-3 guard.",
                "1ba828f4: dated Lu modification-history entries in all 33 changed Fortran modules.",
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
                "For corrected relaxation fixtures, movable atom flags yield nonzero forces and full stress output includes shear components. Graphite method-2 relaxation converges both atoms and cell. Primitive Si and monoclinic HfO2 provide independent six-strain checks, while HfO2 also exercises the full-force finite-difference harness."
            ),
            H("Test runner state"),
            T(
                ["Test", "System/capability", "Primary acceptance signal"],
                [
                    ["010", "Graphite and graphene", "Relaxation, Dirac/K crossings, DOS and pDOS."],
                    ["011", "Monoclinic HfO2", "Ewald force/stress FD, cell CG, basis and MPI invariance."],
                    ["012", "Primitive diamond Si", "EOS, full-cell CG, six strains, bands and pDOS."],
                    ["013", "Rutile TiO2", "Anisotropic oxide regression and Ti-d/O-p projections."],
                    ["014", "Bulk 2H-MoS2", "120-degree layered transition-metal system and d projections."],
                    ["015", "Monoclinic ZrO2", "Second ionic monoclinic material and disconnected path plotting."],
                    ["016", "Triclinic MIC", "Exact closest image versus exhaustive enumeration."],
                    ["017", "Polarization/extxyz", "Equivalent-cell covariance and complete metadata."],
                    ["018", "Graphene vdW-DFT", "Determinant rather than vector-product normalization."],
                    ["019", "Variable-cell MD", "Full-lattice NPT bookkeeping and method-3 guard."],
                ],
                [1.3 * cm, 5.0 * cm, 9.2 * cm],
            ),
            H("Finite differences"),
            P(
                "Primitive Si provides a six-strain driver with machine-readable analytic-versus-numerical derivatives, explicit stress convention, units, and error metrics. The final two-rank rerun has 0.0548 GPa maximum and 0.0360 GPa RMS absolute error. HfO2 applies the same pattern to explicit ionic Ewald, with 0.00155 GPa maximum isolated-ion error and 0.04825 GPa maximum total-stress error."
            ),
            H("Legacy regression"),
            P(
                "Legacy tests 001-004 and 006-009 pass under the permitted one/two-rank configurations. Test 005 is a named four-process PBE0/GTO case; at one or two ranks it fails identically on the clean feature executable and on an independently built untouched Bowler baseline. The user confirms this is a known macOS-only issue that succeeds on Linux and will be treated in another session."
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
                    ["src/io_module.f90", "Reads/writes off-diagonal cells, coordinate transforms, determinant stress, complete extxyz lattice.", "Validated by test 017."],
                    ["src/control.f90", "Initializes lattice state; integrates full stress and full-lattice cell CG; guards method 3.", "Validated method-2 route."],
                    ["src/move_atoms.module.f90", "Affine cell updates, reciprocal/density refresh, full-lattice line search, wrapping conversions.", "Validated by 010-012."],
                    ["src/force_module.f90", "Extends stress contributions and coordinate factors to off-diagonal components.", "Six-strain validated."],
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
                    ["src/constraint_module.f90", "SHAKE periodic wrapping delegated to exact MIC helper.", "Geometry path covered by test 016."],
                    ["src/DFT_D2_module.f90", "Dispersion displacement uses general MIC/length state.", "Substantive; FD test."],
                    ["src/exx_module.f90", "Uses lattice-vector norms for directional grid spacing.", "General geometry conversion; EXX retains feature-specific tests."],
                    ["src/ion_electrostatic_module.f90", "General Ewald lattice, rebuild lifecycle, force and all-six stress.", "Validated by test 011."],
                    ["src/polarisation_module.f90", "Determinant volume and inverse-lattice ionic coordinates.", "Validated by test 017."],
                    ["src/vdWDFT_module.f90", "Determinant reciprocal normalization.", "Validated by test 018."],
                    ["src/md_control_module.f90", "Full-lattice barostat state, determinant volume and covariant updates.", "Validated by test 019."],
                    ["src/md_misc_module.f90", "Writes complete lattice rows to MD frames.", "Validated by test 019."],
                    ["src/md_model_module.f90", "Scalar cell names migrated to length array.", "Compatibility only."],
                    ["src/XLBOMD_module.f90", "Scalar reference migrated to length array.", "Compatibility only."],
                    ["src/initialisation_module.f90", "Synchronizes vector-based cell state during initialization.", "Keeps lattice, inverse, reciprocal, lengths, and determinant consistent."],
                    ["testsuite tests 010-019", "Documented material, derivative, invariance and geometry workflows.", "All ten capability gates validated."],
                ],
                [4.4 * cm, 8.0 * cm, 3.1 * cm],
            ),
        ],
    ),
    (
        "Residual risk register and pull-request acceptance",
        [
            T(
                ["Priority", "Risk", "Evidence", "Acceptance criterion"],
                [
                    ["P1", "Long NPT trajectories", "Test 019 is a one-step geometry gate.", "Characterize drift and ensemble sampling separately from geometry support."],
                    ["P1", "Specialist combinations", "Tests cover representative PAO, oxide, vdW and polarization paths.", "Add feature-specific regressions when claiming SOC, EXX, spin or linear-scaling combinations."],
                    ["P1", "Highly unreduced cell performance", "Exact MIC search is bounded but may inspect many images.", "Optionally reduce the lattice or cache search bounds without changing exactness."],
                    ["P1", "Legacy method 3", "Its parameterization remains orthorhombic.", "Keep the explicit skew-cell guard and direct users to method 2."],
                    ["P2", "Cross-platform compiler coverage", "Full build and tests were run on macOS GNU/OpenMPI.", "Run clean Linux CI builds with GNU and a second compiler."],
                    ["P2", "macOS PBE0/GTO test 005", "Failure reproduces on untouched Bowler baseline at unsupported rank counts.", "Handle in a separate legacy-platform investigation."],
                    ["P2", "Generated test volume", "Reference ions and plots account for most insertions.", "Retain compact summaries and apply repository policy for large fixtures."],
                ],
                [1.2 * cm, 4.1 * cm, 4.6 * cm, 5.6 * cm],
            ),
            H("Physics matrix represented by this branch"),
            B(
                "Orthogonal legacy regression: tests 001-004 and 006-009 pass under the permitted rank counts.",
                "Hexagonal graphite/graphene: method-2 relaxation, bands, total DOS and pDOS.",
                "Primitive Si: familiar material in a 60-degree cell, EOS consistency, six strains and electronic structure.",
                "Monoclinic HfO2: Ewald lifecycle, force/stress derivatives, cell mechanics and MPI/basis invariance.",
                "Monoclinic ZrO2 and hexagonal MoS2: independent chemical and orbital-projection validation.",
                "Strongly skewed triclinic toy cells: exact MIC compared with exhaustive enumeration.",
                "Specialist geometry: polarization, extended XYZ, vdW-DFT normalization, and one-step NPT cell bookkeeping.",
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
        "Completion record and future extensions",
        [
            H("Completed - Curate and lock the core"),
            P(
                "The feature history is based directly on 34de2d61, unrelated EXX formatting is absent, the lattice convention is centralized, and exact MIC plus equivalent-cell tests lock the geometric foundation."
            ),
            H("Completed - Static DFT path"),
            P(
                "Real-space grids, FFT reciprocal vectors, matrix images, pseudopotentials, Hartree/XC stress, Ewald electrostatics, forces and all six stresses are implemented and exercised by the material and finite-difference gates."
            ),
            H("Completed - Relaxation"),
            P(
                "Method 2 preserves fractional atoms, reciprocal coordinates and charge normalization under symmetric strain. Graphite, primitive Si and ionic HfO2 demonstrate cell mechanics; the stale HfO2 core-correction defect is fixed."
            ),
            H("Completed - Specialist geometry"),
            P(
                "Polarization, extended XYZ, vdW-DFT determinant normalization, exact MIC and variable-cell MD bookkeeping have dedicated tests. Unsupported legacy method 3 is rejected rather than silently mis-handled."
            ),
            H("Next integration step - Pull request"),
            P(
                "Push the clean feature branch, run Linux CI and any desired four-rank material references, then attach this report and machine-readable summaries to the pull request. Correcting the remote develop pointer remains a separate repository-administration decision."
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
                "The audit demonstrates why physics confirmation had to proceed capability by capability: the Ewald lifecycle, a stale volume-dependent core correction, exact closest images, polarization coordinates, vdW reciprocal normalization, metadata, and barostat state were independent failure modes. Each now has a corresponding implementation commit and focused test."
            ),
            Q(
                "Final status",
                "General non-90-degree functionality within the declared supported scope: 100 percent complete. Clean branch isolation: complete. Source modification histories: complete. Focused tests 010-019: complete. Remaining work consists of cross-platform CI, normal review, and optional feature-combination or long-trajectory extensions rather than known missing core geometry.",
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
                "# Ionic monoclinic Ewald derivatives and invariance\n"
                "NP=2 ./testsuite/test_011_hfo2/run_ewald_strain_fd.sh\n"
                "./testsuite/test_011_hfo2/run_equivalent_cell_invariance.sh\n\n"
                "# Primitive-Si stress and specialist geometry gates\n"
                "NP=2 ./testsuite/test_012_bulk_Si_primitive_nonorthogonal/run_strain_fd.sh\n"
                "./testsuite/test_016_exact_minimum_image_triclinic/run_exact_mic.sh\n"
                "NP=2 ./testsuite/test_017_nonorthogonal_polarisation_extxyz/run_workflow.sh\n"
                "NP=2 ./testsuite/test_018_nonorthogonal_vdw_graphene/run_workflow.sh\n"
                "NP=2 ./testsuite/test_019_nonorthogonal_npt_md/run_workflow.sh\n\n"
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
                    ["MoS2 reference suite", "testsuite/test_014_bulk_2h_mos2_hexagonal/reference/"],
                    ["ZrO2 reference suite", "testsuite/test_015_monoclinic_zro2/reference/"],
                    ["Exact MIC source gate", "testsuite/test_016_exact_minimum_image_triclinic/"],
                    ["Polarization/extxyz gate", "testsuite/test_017_nonorthogonal_polarisation_extxyz/"],
                    ["Graphene vdW-DFT gate", "testsuite/test_018_nonorthogonal_vdw_graphene/"],
                    ["Variable-cell MD gate", "testsuite/test_019_nonorthogonal_npt_md/"],
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
        r"Status & Supported general-cell scope complete; ready for review\\",
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
        ["Status", "Supported general-cell scope complete; ready for review"],
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
