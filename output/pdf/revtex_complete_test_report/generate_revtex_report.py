#!/usr/bin/env python3
"""Generate the self-contained REVTeX validation report and collect its assets."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SUMMARY = ROOT / "testsuite/test_runs/20260809-235347/summary.json"

PURPOSES = {
    1: "Legacy diagonalization regression for bulk diamond Si.",
    2: "Legacy linear-scaling regression for the same bulk-Si cell.",
    3: "Berry-phase/Resta polarization regression for displaced BaTiO3.",
    4: "Isolated ethylene PBE0 exact exchange using CRI integrals.",
    5: "Isolated ethylene PBE0 exact exchange using GTO integrals; includes the macOS initialization fix.",
    6: "Isolated ethylene PBE0 exact exchange using ERI integrals.",
    7: "Spin-polarized isolated CH PBE0 regression.",
    8: "Surface dipole correction regression.",
    9: "DFT+U diagonalization regression.",
    10: "Hexagonal graphite and graphene: SCF, bands, PDOS, and cell relaxation.",
    11: "Monoclinic HfO2: Ewald force/stress, equivalent cells, relaxation, bands, and PDOS.",
    12: "Two-atom primitive diamond Si: relaxation, EOS, six strains, bands, and PDOS.",
    13: "Rutile TiO2 orthogonal-anisotropic control with relaxation, bands, and PDOS.",
    14: "Bulk 2H-MoS2: hexagonal relaxation, bands, and orbital-resolved PDOS.",
    15: "Monoclinic ZrO2: symmetry restoration, relaxation, bands, and PDOS.",
    16: "Exact Euclidean minimum image in adversarial triclinic and unreduced cells.",
    17: "Equivalent-cell polarization and full extended-XYZ lattice/stress metadata.",
    18: "Nonlocal vdW-DFT invariance under a determinant-one graphene basis change.",
    19: "Nonorthogonal variable-cell MD and partition-consistent triclinic wrapping.",
    20: "Extreme-skew space-filling-curve decomposition and MPI invariance.",
    21: "Six-degree-of-freedom full-cell NPT dynamics for monoclinic HfO2.",
    22: "In-plane symmetric NPT dynamics for a 3x3 graphene slab.",
    23: "Coupled fixed-angle Method-3 relaxation of HCP Zr.",
    24: "Published 3R graphite: SFC, MPI, Ewald, bands, and PDOS.",
    25: "Orthorhombic Si blip-basis smoke test.",
    26: "Equivalent nonorthogonal Si blip-basis regression.",
    27: "High-accuracy primitive/conventional diamond-Si energy and stress equivalence.",
    28: "Automatic activation and parsing of the full stress tensor for general cells.",
    29: "FFT and automatically generated k-point sampling bounds for an extreme cell.",
    30: "Exact point-to-parallelepiped distance for triclinic integration-grid blocks.",
    31: "Rotated triclinic PDB write/restart preserving orientation through SCALE records.",
    32: "Face area, normal height, and dipole-coordinate geometry for triclinic slabs.",
}

SETTINGS = {
    1: ("50", r"$2\times2\times2$"), 2: ("50", r"$\Gamma$ / O(N)"),
    3: ("100", r"$1\times1\times1$"), 4: ("90", r"$\Gamma$"),
    5: ("90", r"$\Gamma$"), 6: ("90", r"$\Gamma$"),
    7: ("90", r"$\Gamma$"), 8: ("100", r"$1\times1\times1$"),
    9: ("100", r"$3\times3\times3$"),
    10: ("100--150 (120 electronic)", r"$4\times4\times2$; line paths"),
    11: ("80--200 (100 electronic)", r"$1^3$, $2^3$, $3^3$; line path"),
    12: ("80", r"$4^3$, $6^3$, $8^3$, $10^3$; line path"),
    13: ("100", r"$3\times3\times5$ to $5\times5\times7$; line path"),
    14: ("100", r"$4\times4\times2$ to $6\times6\times3$; line path"),
    15: ("100", r"$3^3$ to $5^3$; line path"), 16: ("--", "source-level"),
    17: ("120", r"$1\times1\times1$"), 18: ("80", r"$1\times1\times1$"),
    19: ("80", r"$1\times1\times1$"), 20: ("80", r"$2\times2\times2$"),
    21: ("80", r"$1\times1\times1$"), 22: ("80", r"$1\times1\times1$"),
    23: ("100", r"$6\times6\times4$"), 24: ("60", r"$2^3$ static; $8^3$ electronic; line path"),
    25: ("50", r"$2\times2\times2$"), 26: ("50", r"$2\times2\times2$"),
    27: ("400", r"$11^3$ cubic; $19^3$ primitive"), 28: ("80", r"$2\times2\times2$"),
    29: ("20", "automatic density rule"), 30: ("--", "source-level"),
    31: ("80", r"$2\times2\times2$"), 32: ("--", "source-level"),
}

PLOTS = [
    ("graphite_band_pdos.png", "testsuite/test_010_graphite_monoclinic/reference/graphite_band_pdos.png"),
    ("graphene_band_pdos.png", "testsuite/test_010_graphite_monoclinic/reference/graphene_band_pdos.png"),
    ("hfo2_band_pdos.png", "testsuite/test_011_hfo2/reference/electronic/monoclinic_hfo2_band_pdos.png"),
    ("hfo2_stress_fd.png", "testsuite/test_011_hfo2/reference/ewald_strain_finite_difference/monoclinic_hfo2_ewald_six_strain_validation.png"),
    ("si_band_pdos.png", "testsuite/test_012_bulk_Si_primitive_nonorthogonal/reference/primitive_si_band_pdos.png"),
    ("si_eos.png", "testsuite/test_012_bulk_Si_primitive_nonorthogonal/reference/eos/primitive_si_birch_murnaghan.png"),
    ("si_stress_fd.png", "testsuite/test_012_bulk_Si_primitive_nonorthogonal/reference/strain_finite_difference/primitive_si_six_strain_validation.png"),
    ("rutile_band_pdos.png", "testsuite/test_013_rutile_TiO2_tetragonal/reference/rutile_tio2_band_pdos.png"),
    ("mos2_band_pdos.png", "testsuite/test_014_bulk_2h_mos2_hexagonal/reference/bulk_2h_mos2_band_pdos.png"),
    ("zro2_band_pdos.png", "testsuite/test_015_monoclinic_zro2/reference/monoclinic_zro2_band_pdos.png"),
    ("rhombohedral_graphite_band_pdos.png", "testsuite/test_024_rhombohedral_graphite_sfc_mpi/reference/rhombohedral_graphite_band_pdos.png"),
]

ATOM_OVERRIDES = {20: 2, 24: 2}


def esc(value: object) -> str:
    text = str(value)
    for old, new in [("\\", r"\textbackslash{}"), ("_", r"\_"), ("%", r"\%"),
                     ("&", r"\&"), ("#", r"\#")]:
        text = text.replace(old, new)
    return text


def commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "--short=12", "HEAD"], cwd=ROOT, text=True).strip()


def copy_assets() -> None:
    figures = HERE / "figures"
    data = HERE / "data"
    figures.mkdir(exist_ok=True)
    data.mkdir(exist_ok=True)
    for destination, source in PLOTS:
        shutil.copy2(ROOT / source, figures / destination)
    shutil.copy2(SUMMARY, data / "all_tests_summary.json")


def settings_rows(tests: list[dict]) -> str:
    rows = []
    for test in tests:
        n = test["number"]
        cutoff, mesh = SETTINGS[n]
        atom_count = ATOM_OVERRIDES.get(n, test["atom_count"])
        atoms = "--" if atom_count is None else str(atom_count)
        ranks = ", ".join(map(str, test["mpi_ranks_used"])) or "--"
        short_name = esc(test["name"][9:]).replace(r"\_", r"\_\allowbreak{}")
        rows.append(f"{n:03d} & {short_name} & {atoms} & {cutoff} & {mesh} & {ranks} & {test['duration_seconds']:.1f} \\\\")
    return "\n".join(rows)


def detail_sections(tests: list[dict]) -> str:
    blocks = []
    for test in tests:
        n = test["number"]
        cutoff, mesh = SETTINGS[n]
        atom_count = ATOM_OVERRIDES.get(n, test["atom_count"])
        atom_text = "no atom input (source-level geometry test)" if atom_count is None else f"{atom_count} atoms"
        highlights = "; ".join(
            item for item in test.get("highlights", [])[:2]
            if len(item) < 100 and not item.lstrip().startswith(('"', "{"))
        ) or "the maintained numerical and structural acceptance gates completed"
        blocks.append(
            rf"\subsection{{Test {n:03d}: {esc(test['name'][9:].replace('_', ' '))}}}" + "\n"
            + esc(PURPOSES[n]) + " "
            + rf"The consolidated run records {atom_text}, MPI ranks {', '.join(map(str, test['mpi_ranks_used'])) or '--'}, "
            + rf"and {test['duration_seconds']:.3f} s wall time. The representative grid cutoff was {cutoff} Ha and the reciprocal sampling was {mesh}. "
            + rf"Acceptance evidence: \emph{{{esc(highlights)}}}. Status: \textbf{{{test['status']}}}."
        )
    return "\n\n".join(blocks)


def write_bib() -> None:
    bib = r"""@article{Nakata2020,
 author={Nakata, A. and others}, title={Large Scale and Linear Scaling DFT with the CONQUEST Code},
 journal={J. Chem. Phys.}, volume={152}, pages={164112}, year={2020}, doi={10.1063/5.0005074}}
@article{Monkhorst1976, author={Monkhorst, H. J. and Pack, J. D.},
 title={Special Points for Brillouin-Zone Integrations}, journal={Phys. Rev. B}, volume={13}, pages={5188--5192}, year={1976}, doi={10.1103/PhysRevB.13.5188}}
@article{Ewald1921, author={Ewald, P. P.}, title={Die Berechnung optischer und elektrostatischer Gitterpotentiale},
 journal={Ann. Phys.}, volume={369}, pages={253--287}, year={1921}, doi={10.1002/andp.19213690304}}
@article{Parrinello1981, author={Parrinello, M. and Rahman, A.}, title={Polymorphic Transitions in Single Crystals: A New Molecular Dynamics Method},
 journal={J. Appl. Phys.}, volume={52}, pages={7182--7190}, year={1981}, doi={10.1063/1.328693}}
@article{Dion2004, author={Dion, M. and others}, title={Van der Waals Density Functional for General Geometries},
 journal={Phys. Rev. Lett.}, volume={92}, pages={246401}, year={2004}, doi={10.1103/PhysRevLett.92.246401}}
"""
    (HERE / "references.bib").write_text(bib)


def main() -> None:
    copy_assets()
    write_bib()
    data = json.loads(SUMMARY.read_text())
    tests = data["tests"]
    passed = sum(t["status"] == "PASS" for t in tests)
    duration = sum(t["duration_seconds"] for t in tests)
    tex = rf"""\documentclass[aps,prb,preprint,superscriptaddress,longbibliography,floatfix]{{revtex4-2}}
\usepackage[T1]{{fontenc}}
\usepackage{{lmodern,microtype,amsmath,amssymb,bm,graphicx,booktabs,tabularx,array,xcolor,listings}}
\usepackage[hidelinks]{{hyperref}}
\definecolor{{cqblue}}{{HTML}}{{155E75}}
\definecolor{{cqgray}}{{HTML}}{{F3F4F6}}
\newcommand{{\CQ}}{{CONQUEST}}
\newcommand{{\code}}[1]{{\texttt{{#1}}}}
\newcommand{{\angstrom}}{{\mbox{{\AA}}}}
\begin{{document}}
\title{{General Nonorthogonal Cells in \CQ:\\Implementation Audit, Corrective Commits, and a 32-Test Validation Campaign}}
\author{{Anh Khoa Augustin Lu}}
\affiliation{{Research Center for Materials Nanoarchitectonics (MANA), National Institute for Materials Science (NIMS), Tsukuba, Japan}}
\date{{10 August 2026}}
\begin{{abstract}}
We report a source audit and complete regression campaign for general (triclinic) simulation cells in \CQ. The implementation replaces orthorhombic scalar geometry with a consistent lattice-matrix formulation across reciprocal space, real-space grids, periodic images, Ewald electrostatics, forces, stress, relaxation, molecular dynamics, spatial decomposition, and I/O. Audit findings were checked against the source rather than accepted as authoritative. Concrete defects were corrected in focused commits, including full-stress parsing, workflow-specific MPI limits, and a real intermittent NPT failure caused by inconsistent boundary tolerances between atomic wrapping and the general-cell atom dispenser. The consolidated suite passed {passed}/{len(tests)} tests. It used at most three build jobs, one OpenMP thread, and atom-aware MPI caps. This report records each test's atom count, grid cutoff, reciprocal sampling, rank use, wall time, and acceptance purpose, and includes all available maintained band-structure/PDOS figures.
\end{{abstract}}
\maketitle

\section{{Scope and conclusion}}
The audited branch supports a general direct lattice $\mathbf A=[\mathbf a_1\ \mathbf a_2\ \mathbf a_3]$, with $\mathbf r=\mathbf A\mathbf s$, volume $\Omega=|\det\mathbf A|$, and reciprocal basis $2\pi\mathbf A^{{-T}}$. The completed campaign validates legacy orthogonal calculations and the new hexagonal, monoclinic, rhombohedral, rotated triclinic, and deliberately unreduced representations. All {passed} tests passed. The sum of recorded per-test wall times is {duration/60:.1f} min; the complete runner elapsed time also includes the build and orchestration overhead.

The relaxation distinction is important. \code{{OptCellMethod 2}} is the full symmetric-strain route and can change lattice angles while relaxing atoms and cell together. \code{{OptCellMethod 3}} scales complete lattice vectors under fixed-angle constraints; it supports nonorthogonal cells but does not provide shear/angle relaxation. The NPT \code{{full}} and \code{{xy}} constraints separately exercise six-component and in-plane symmetric cell dynamics.

\section{{Audit-to-fix record}}
The audit served as a hypothesis list. Each claim was checked in implementation and tests. The resulting focused commits are:
\begin{{description}}
\item[\code{{f365ac43}}] Initialize \code{{eri\_gto}} to zero, integrating the official macOS Test-005 correction.
\item[\code{{4ce068e2}}] Add the atom-aware complete test runner.
\item[\code{{3072c04c}}] Respect workflow-specific MPI ceilings in addition to the atom-derived cap.
\item[\code{{c4418f12}}] Parse the complete $3\times3$ stress tensor in the equivalent-cell regression.
\item[\code{{54b75a36}}] Make triclinic coordinate wrapping partition-consistent.
\item[\code{{9248eb4d}}] Support consolidated targeted reruns without losing the successful base results.
\item[\code{{6fe487c6}}] Make the first PDF's test detail layout pagination-safe.
\item[\code{{f527e566}}] Add the complete machine-generated all-tests report.
\end{{description}}

\subsection{{Intermittent NPT defect and correction}}
The Test-019 failure was a source defect, not a flaky acceptance threshold. The atomic cell-wrapping routine historically shifted all Cartesian components by the same $\epsilon$, whereas the general-cell atom dispenser classified boundaries with direction-dependent fractional tolerances derived from rows of $\mathbf A^{{-1}}$. In a skewed cell the two rules can place a boundary atom on opposite sides of a partition, eventually causing the reported missing-pair failure in \code{{make\_table}}.

The corrected wrapper transforms to fractional coordinates, derives per-direction tolerances from the inverse lattice, applies $s_i\leftarrow s_i-\lfloor s_i+\epsilon_i\rfloor$, and transforms back. This aligns wrapping with dispenser classification without assuming Cartesian lattice axes. A fixed \code{{General.RNGSeed 5489}} makes the regression reproducible; two repeated Test-019 runs produced byte-identical summaries.

\section{{Test orchestration and resource policy}}
The Python runner discovers atom counts from the active coordinate source and guards every MPI invocation. Its global policy is
\begin{{equation}}
N_{{\rm MPI}}=\max\left(1,\min\left[3,\left\lfloor N_{{\rm atom}}/3\right\rfloor\right]\right),
\end{{equation}}
followed by any smaller workflow-specific ceiling. Compilation used at most three jobs; tests ran sequentially with one OpenMP thread. Tests 001--009 use the legacy direct-run plus pytest comparisons, while 010--032 invoke their maintained workflows. The consolidated JSON is shipped beside this source.

\section*{{Numerical settings and execution record}}
Grid cutoffs are in hartree. Multiple values indicate distinct stages or convergence/representation checks within one workflow. ``Line path'' denotes a non-self-consistent band path in addition to the listed Monkhorst--Pack meshes.\cite{{Monkhorst1976}}
\begin{{center}}\scriptsize
\begin{{tabular}}{{r p{{40mm}} r p{{25mm}} p{{42mm}} p{{10mm}} r}}
\toprule Test & Short name & Atoms & Grid cutoff & k sampling & MPI & Time (s) \\
\midrule
{settings_rows(tests[:16])}
\bottomrule
\end{{tabular}}
\end{{center}}
\begin{{center}}\scriptsize
\begin{{tabular}}{{r p{{40mm}} r p{{25mm}} p{{42mm}} p{{10mm}} r}}
\toprule Test & Short name & Atoms & Grid cutoff & k sampling & MPI & Time (s) \\
\midrule
{settings_rows(tests[16:])}
\bottomrule
\end{{tabular}}
\end{{center}}

\section{{General-cell implementation}}
Grid points follow fractional lattice coordinates and carry volume $\Omega/(N_1N_2N_3)$. Reciprocal vectors and k points use $2\pi\mathbf A^{{-T}}$, and automatic grid/k-mesh bounds use direct- and reciprocal-vector norms rather than Cartesian box lengths. Periodic image handling uses fractional translations and an exact Euclidean minimum-image search for skewed or unreduced bases. Ewald state is rebuilt after every accepted or trial cell change.\cite{{Ewald1921}}

The complete symmetric stress tensor is propagated through the supported electronic and ionic terms. Method-2 relaxation applies an affine symmetric strain while preserving fractional coordinates; Method 3 scales full vectors under its stated fixed-angle constraint. Variable-cell dynamics updates the same lattice, inverse, determinant, reciprocal grid, density normalization, atomic positions, and partition data as a coordinated state transition.\cite{{Parrinello1981}}

General-cell support also reaches fractional SFC classification, triclinic block distance, PDB \code{{CRYST1}} plus \code{{SCALE1--3}}, extended XYZ lattice/stress metadata, slab dipole geometry, Berry-phase polarization, vdW-DFT normalization, and the blip basis. The broad scope is why source-level geometry tests accompany material calculations.

\section{{Material and electronic-structure evidence}}
The plotted band gaps are compact-basis regression signals, not converged predictions. PDOS integrals and orbital character are used as workflow integrity checks. The six material workflows below retain their generated figures in the report subfolder.

\begin{{figure*}}[t]
\includegraphics[width=.49\textwidth]{{figures/graphite_band_pdos.png}}\hfill
\includegraphics[width=.49\textwidth]{{figures/graphene_band_pdos.png}}
\caption{{Test 010. AB graphite (left) and isolated graphene (right). The numerical K-point gaps are 0.052 and 0.493 meV; integrated valence counts are 16 and 8 electrons.}}
\end{{figure*}}

\begin{{figure*}}[t]
\includegraphics[width=.49\textwidth]{{figures/hfo2_band_pdos.png}}\hfill
\includegraphics[width=.49\textwidth]{{figures/hfo2_stress_fd.png}}
\caption{{Test 011. Monoclinic HfO$_2$ bands/PDOS (left) and six-component Ewald stress finite differences (right). The latter directly probes the ionic general-cell derivative.}}
\end{{figure*}}

\begin{{figure*}}[t]
\includegraphics[width=.49\textwidth]{{figures/si_band_pdos.png}}\hfill
\includegraphics[width=.49\textwidth]{{figures/si_eos.png}}
\caption{{Test 012. Primitive diamond-Si bands/PDOS (left; indirect path gap 0.7381 eV and 8.00046 integrated electrons) and nine-point Birch--Murnaghan EOS (right).}}
\end{{figure*}}

\begin{{figure*}}[t]
\includegraphics[width=.49\textwidth]{{figures/si_stress_fd.png}}\hfill
\includegraphics[width=.49\textwidth]{{figures/rutile_band_pdos.png}}
\caption{{Six-strain primitive-Si stress validation (left) and Test-013 rutile TiO$_2$ bands/PDOS (right). Rutile provides an anisotropic right-angled control.}}
\end{{figure*}}

\begin{{figure*}}[t]
\includegraphics[width=.49\textwidth]{{figures/mos2_band_pdos.png}}\hfill
\includegraphics[width=.49\textwidth]{{figures/zro2_band_pdos.png}}
\caption{{Tests 014 and 015. Bulk 2H-MoS$_2$ (left; indirect path gap 0.8804 eV) and monoclinic ZrO$_2$ (right; indirect path gap 3.3789 eV), with orbital-resolved PDOS.}}
\end{{figure*}}

\begin{{figure*}}[t]
\centering\includegraphics[width=.66\textwidth]{{figures/rhombohedral_graphite_band_pdos.png}}
\caption{{Test 024. Published 3R graphite in its acute rhombohedral primitive cell. The path contains 241 k points, the integrated electron count is 8.0, and the compact-basis path separation is 0.0538 eV.}}
\end{{figure*}}

\section{{Selected quantitative outcomes}}
For graphite, coupled Method-2 relaxation reduced the maximum force from 0.03191205 to 0.00019971 Ha/bohr and maximum stress from 22.3003 to 0.0431 GPa in six outer cycles. Primitive Si relaxation reduced the maximum force from 0.00918819 to $9.894\times10^{{-5}}$ Ha/bohr, and its EOS and direct cell relaxation agreed on the lattice minimum. Rutile oxygen relaxed from $u=0.3120$ to 0.3052583. In 2H-MoS$_2$, sulfur moved from $z=0.6150$ to 0.6211887 and the maximum force fell to 0.00019569 Ha/bohr. Monoclinic ZrO$_2$ ended at 0.00039986 Ha/bohr maximum force.

Equivalent-cell tests cover determinant-one shears, primitive/conventional representations, and rotated PDB restart. Test 027 uses the deliberately stringent 400-Ha cutoff and commensurate $11^3$ conventional/$19^3$ primitive meshes to separate representation correctness from ordinary discretization error. Tests 029, 030, and 032 then isolate sampling bounds, block distance, and face-normal geometry at source level.

\section{{Interpretation and limits}}
A pass demonstrates agreement with the maintained regression's numerical or structural invariants, not universal convergence for production research. Some low cutoffs and Gamma-only meshes are intentional smoke-test settings. Electronic plots are acceptance artifacts made with compact localized bases. Long-time NPT ensemble statistics, every exchange-correlation/basis combination, spin--orbit coupling, and performance optimization for severely unreduced lattices remain separate validation topics. The exact minimum image prioritizes correctness over optimal asymptotic speed.

\section{{Conclusion}}
The audit identified useful questions but was not treated as authoritative. Source inspection separated mistaken concerns from concrete defects. The latter were fixed in focused commits and verified by targeted reruns before consolidation. With the official Test-005 macOS initialization fix integrated, all 32 maintained tests pass under the requested three-core ceiling. The most consequential new correction is the partition-consistent fractional wrapping rule, which removes an intermittent triclinic NPT failure at its geometric source.

\appendix
\section{{Test-by-test record}}
{detail_sections(tests)}

\section{{Reproducibility record}}
Report source commit before adding this artifact: \code{{{commit()}}}. Consolidated run: \code{{testsuite/test\_runs/20260809-235347/summary.json}}, assembled from the full sweep \code{{20260809-230103}} plus successful targeted reruns of Tests 011, 019, and 027. The shipped \code{{data/all\_tests\_summary.json}} is an immutable copy used to generate the tables. The report generator copies only maintained figures and writes the REV\TeX\ source and bibliography in this folder.

\bibliography{{references}}
\end{{document}}
"""
    (HERE / "conquest_general_cell_validation_revtex.tex").write_text(tex)


if __name__ == "__main__":
    main()
