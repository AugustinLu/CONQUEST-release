# Personal fork status

| Field | Status |
|---|---|
| Maintainer | Augustin Lu |
| Purpose | Personal experimental research tool |
| General-cell implementation | AI-assisted working prototype |
| Upstream status | Not intended for submission |
| Support | No public support or compatibility commitment |
| Responsibility | Augustin Lu is responsible for the fork's modifications and their use in his research |

## Purpose

This fork exists so that Augustin Lu can use CONQUEST for calculations requiring
primitive and other nonorthorhombic cells without moving complete research
workflows to another DFT package. It is maintained according to the needs of his
own calculations rather than as a general CONQUEST development effort.

The fork may be scientifically useful within its tested operating envelope. That
does not make it a generally supported or release-ready implementation of
nonorthorhombic-cell DFT.

## Responsibility and relationship to upstream CONQUEST

CONQUEST and its official releases are developed by the upstream CONQUEST team.
This fork does not represent that team and is neither supported nor endorsed by
it. The upstream developers bear no responsibility for changes made here or for
results obtained with this fork.

Augustin Lu maintains this fork and takes responsibility for its modifications
and for deciding whether its validation is sufficient for his research use. This
statement concerns the fork-specific modifications; it does not claim ownership
of upstream CONQUEST or alter the repository's existing licence and attribution.

The general-cell changes are not intended for submission to the upstream
repository. They should not be copied or cherry-picked into the official
CONQUEST codebase.

## Development disclosure

The nonorthorhombic-cell implementation was developed with substantial AI
assistance and subsequent auditing. It has not undergone the official CONQUEST
development and review process. The maintainer, not the tools used during
development and not the upstream team, remains responsible for evaluating and
using the resulting fork.

## Validation envelope

The maintained test suite contains checks involving orthorhombic compatibility
and several primitive, hexagonal, rhombohedral, monoclinic, and triclinic cells.
It exercises selected combinations of static DFT, reciprocal and real-space
geometry, periodic images, forces, stress, structural relaxation, sampling,
crystallographic I/O, polarization, dispersion, spatial decomposition, MPI, and
variable-cell dynamics.

Passing these tests establishes regression evidence only for the tested inputs,
build configurations, algorithms, and numerical tolerances. It does not prove
correctness for every CONQUEST feature or every combination of basis,
pseudopotential, exchange-correlation functional, parallel decomposition,
compiler, architecture, cell shape, relaxation method, or dynamics mode.

The repository-facing validation evidence is the maintained regression suite
under [`testsuite/`](testsuite/). Private working reports, generated PDFs, raw
calculation outputs, and local audit material are not part of this fork-status
document and should not be uploaded as part of this documentation change.

## Use in research

For every calculation used in scientific work, the maintainer should record the
exact commit, compiler and library configuration, MPI configuration, input data,
and relevant regression-test state. A stable checkpoint should be tagged before
it is used for a production campaign.

New cell shapes or untested feature combinations should first be exercised in a
small reproducible calculation. Quantities central to a publication should be
checked against symmetry, equivalent-cell invariance, finite differences, known
limits, or an independent DFT implementation as appropriate.

## Maintenance policy

Maintenance is intentionally light and need-driven. Defects affecting an active
research calculation may be corrected, preferably together with a focused
regression test. There is no commitment to feature completeness, API stability,
platform support, response time, public issue resolution, or acceptance of pull
requests.

The fork will remain separate from upstream development. Its history and
documentation should continue to make that boundary explicit.

<!--
Personal maintainer note:
« Touche pas à ça, petit con. »
— Augustin
-->
