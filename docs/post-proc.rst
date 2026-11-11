.. _post-proc:

===============================
Post-processing CONQUEST output
===============================

.. _pp_intro:

Introduction
++++++++++++

The utility ``PostProcessCQ`` allows users to post-process the output
of a CONQUEST calculation, to produce structure files, densities of
states, and charge density, band
densities and STM images as CUBE
files (which can be read by the freely available `VESTA
<https://jp-minerals.org/vesta/en/>`_ code).

There are a number of different analyses which can be performed:
coordinate conversion (to formats which can be plotted); conversion of
total charge density to CUBE file format; production of band-resolved
(optionally k-point resolved) densities in CUBE file format; simple
Tersoff-Hamann STM simulation; calculation of densities of states,
including projected DOS; and Berry-phase polarisation, mode effective
charges and Born effective charges (:ref:`pp_berry`).  You should ensure that all the files
produced during the CONQUEST run are available for the post-processing
(including ``eigenvalues.dat``, ``chden.NNN``, ``make_blk.dat`` or
``hilbert_make_blk.dat`` and ``ProcessNNNNNNNWF.dat`` and
``ProcessSijNNNNNNNWF.dat`` as applicable) as well as the input files.

**Note** that the utility reads the ``Conquest_input`` file, taking some
flags from the CONQUEST run that generated the output, and some
utility-specific flags that are detailed below.

**Note also** that projected DOS, band density and STM simulation are
not at present compatible with multi-site support functions (MSSF),
though we hope to implement this soon.

Go to :ref:`top <post-proc>`.

.. _pp_coord:

Coordinate conversion
+++++++++++++++++++++

Set ``Process.Job coo`` to output a coordinate file for further
processing or plotting.  The utility will read the file specified by
``Process.Coordinates`` (which defaults to the file specified by
``IO.Coordinates``).  The output format is selected by specifying the
``Process.CoordFormat`` tag.  The default output format is XYZ (which
adds a ``.xyz`` suffix to the file name) using ``xyz``.  The CASTEP
``.cell`` output format can also be selected using ``cell``.  We plan to
expand this conversion to other formats in the future.

**Note** that for a structural relaxation or molecular dynamics
calculation, if you do not specify ``Process.Coordinates`` then the
``IO.Coordinates`` file, which will be converted, will be the *input*
structure, not the output structure.  Parameters that can be set are:

::

   Process.Coordinates string (default: IO.Coordinates value)
   Process.CoordFormat string (default: xyz; options: xyz, cell)

Go to :ref:`top <post-proc>`.

.. _pp_charge:

Charge density
++++++++++++++

Setting ``Process.Job`` to ``cha``, ``chg`` or ``den`` will convert
the files ``chden.NNN`` which are written by CONQUEST to a cube file.
The processing will use the files ``chden.NNN``, ``Conquest_input``
and ``hilbert_make_blk.dat`` or ``raster_make_blk.dat``.  Parameters
that can be set include:

::
   
   Process.ChargeStub string (default: chden)

The ChargeStub simply defines the filename which will be read, and
used for output.

**Note** that to output the ``chden.NNN`` files from CONQUEST, you must
set the flag ``IO.DumpChargeDensity T`` in the CONQUEST run.

Go to :ref:`top <post-proc>`.

.. _pp_band_dens:

Band density
++++++++++++

Setting ``Process.Job`` to ``ban`` produces band densities from wave
function coefficients output by CONQUEST.  The CONQUEST run must have
the following tags set:

::

   IO.outputWF T

A set of bands whose coefficients are output are specified either with
an energy range (the default is to produce *all* bands):

::

   IO.WFRangeRelative T/F
   IO.min_wf_E real (Ha)
   IO.max_wf_E real (Ha)

or with a list of bands:

::

   IO.maxnoWF n

   %block WaveFunctionsOut
   n entries, each a band number
   %endblock

The wavefunction range can be relative to the Fermi level
(``IO.WFRangeRelative T``) otherwise it is absolute.  Either of these
will produce a file containing all eigenvalues at all k-points
(``eigenvalues.dat``) and a series of files containing the
wavefunction expansion coefficients for the selected bands
(``ProcessNNNNNNNWF.dat``).  These files are output as binary
(unformatted) by default (this can be changed by setting
``IO.MatrixFile.BinaryFormat F`` before the CONQUEST run) and will be
read using the same format (it is important to check this!).

From these wavefunction coefficient files, band densities can be
produced in post-processing, using similar tags; either a range:

::

   Process.min_wf_E real (Ha)
   Process.max_wf_E real (Ha)
   Process.WFRangeRelative T/F

or an explicit list of bands:

::

   Process.noWF n

   %block WaveFunctionsProcess
   n entries, each a band number
   %endblock

Note that the bands to be processed must be a subset of the bands
output by CONQUEST.  The bands can be output summed over k-points, or
at individual k-points, by setting ``Process.outputWF_by_kpoint`` to
``F`` or ``T`` respectively.

Go to :ref:`top <post-proc>`.

.. _pp_STM:

Tersoff-Hamann STM simulation
+++++++++++++++++++++++++++++

Setting ``Process.Job ter`` will use a very simple Tersoff-Hamann
approach to STM simulation, summing over band densities between the
Fermi level and the bias voltage (this is often surprisingly
accurate).  The following parameters can be set:

::

   STM.BiasVoltage    real (eV)
   STM.FermiOffset    real (eV)
   Process.MinZ       real (Bohr)
   Process.MaxZ       real (Bohr)
   Process.RootFile   string (default: STM)

The ``FermiOffset`` tag allows the user to shift the Fermi level (to simulate
charging or an external field).  The height of the simulation cell
in which the STM image is calculated is set by the ``MinZ`` and
``MaxZ`` tags, and the filename by the ``RootFile`` tag.

Go to :ref:`top <post-proc>`.

.. _pp_DOS:

Density of states (DOS)
+++++++++++++++++++++++

Setting ``Process.Job dos`` will produce a total density of states
(DOS) for the system, using the eigenvalues output by CONQUEST.  The
following parameters can be set:

::

   Process.min_DOS_E       real    (Ha, default lowest eigenvalue)
   Process.max_DOS_E       real    (Ha, default highest eigenvalue)
   Process.WFRangeRelative T/F
   Process.sigma_DOS       real    (Ha, default 0.001)
   Process.n_DOS           integer (default 1001)

The limits for the DOS are set by the first two parameters (note that
CONQUEST will output all eigenvalues).  These limits can be given as
absolute energies, or relative to the Fermi level, depending on whether
``WFRangeRelative`` is set to ``F`` or ``T`` respectively.
The broadening applied to each state is set by
``sigma_DOS``, while the number of bins is set by ``n_DOS``.  The
integrated DOS is also calculated; the user can choose whether this
is the total integrated DOS (i.e. from the lowest eigenvalue,
regardless of the lower limit for DOS) or just the local integrated
DOS (i.e. over the interval specified for the DOS) by setting
``Process.TotalIntegratedDOS`` to ``T`` or ``F``, respectively.

If the user does not specify limits on the DOS, then the range will
be expanded slightly so that the broadened peaks fit completely within
the DOS range.  This behaviour can be controlled with an additional
parameter ``Process.ExpandRange T/F`` (the default behaviour is false
if the user sets any limits, otherwise true).

We recommend that, for accurate DOS, CONQUEST should be run
non-self-consistently with a very high k-point density, after reading
in a well-converged input charge density: set ``minE.SelfConsistent
F`` and ``General.LoadRho T`` (which will require that the converged
charge density is written out by CONQUEST by setting ``IO.DumpChargeDensity T``).

Go to :ref:`top <post-proc>`.

.. _pp_pDOS:

Atom-projected DOS
++++++++++++++++++

Setting ``Process.Job pdos`` will produce a total density of states as
above, as well as the density of states projected onto the individual
atoms.  Given support functions :math:`\phi_{i\alpha}(\mathbf{r})`
which are the basis functions of the Kohn-Sham eigenstates
:math:`\psi_{n}(\mathbf{r}) = \sum_{i\alpha}
c^{n}_{i\alpha}\phi_{i\alpha}(\mathbf{r})`, then the projection of a
given state, :math:`n`, onto an atom :math:`i` can be written as
:math:`\sum_{\alpha j\beta} c^{n}_{i\alpha}
S_{i\alpha,j\beta}c^{n\mathbf{k}}_{j\beta}`.  The projected DOS is
constructed using these projections.

If using :ref:`pseudo-atomic orbitals (PAOs) <basis_paos>` as the
basis set, then the atom-projected DOS can be further resolved by
angular momentum (either just :math:`l` or both :math:`l` and
:math:`m`).  If using :ref:`pseudo-atomic orbitals (PAOs)
<basis_paos>` with :ref:`multi-site support functions <basis_mssf>` or
:ref:`blip functions <basis_blips>` then it is not possible to
decompose the DOS any further (in future, it may be possible to
resolve the MSSF coefficients into the individual PAOs, and hence
decompose pDOS by angular momentum).  To output the necessary
coefficients to produce atom-projected DOS, a CONQUEST run must be
performed with the following parameters set:

::

   IO.writeDOS T
   IO.write_proj_DOS T

As for the DOS, very high Brillouin zone sampling is required for
accurate projected DOS, which is most efficiently generated using a
converged charge density and a non-self-consistent calculation with
much higher k-point density.  CONQUEST will produce the wavefunction
files (``ProcessNNNNNNNWF.dat`` and ``ProcessSijNNNNNNNWF.dat``) as
binary (unformatted) by default (change using the flag
``IO.MatrixFile.BinaryFormat F``).

Once the files have been generated by CONQUEST, the output can be
processed by setting the output tag:

::
   
   Process.Job pdos

This is all that is needed for the simplest output.  The number of
bins and smearing of the peaks can be set using:

::

   Process.sigma_DOS 0.002
   Process.n_DOS 10001
   
To resolve the DOS by angular momentum as well as by atom, then the
following flags can be set:

::

   Process.pDOS_l_resolved T
   Process.pDOS_lm_resolved T

Note that only one of these is needed, depending on what level of
resolution is required.  At present, angular momentum resolution is
only available for the PAO basis set (not MSSF or blips) though it
is under development for the MSSF basis (by projection onto the
underlying PAO basis).

The energy range for the projected DOS can
also be specified:

::
   
   Process.min_DOS_E -0.35
   Process.max_DOS_E  0.35
   Process.WFRangeRelative T

where the final tag specifies that the limits on the DOS are given
relative to the Fermi level.

If you only want to produce pDOS for a few atoms, then you can set
the  variable ``Process.n_atoms_pDOS`` and list the atoms you want
in the block ``pDOS_atoms``:

::

   Process.n_atoms_pDOS 2
   %block pDOS_atoms
   1
   12
   %endblock

Go to :ref:`top <post-proc>`.

.. _pp_band_str

Band structure
++++++++++++++

The band structure of a material can be generated by CONQUEST by performing
a non-self-consistent calculation, after reading a well-converged charge density:
set ``minE.SelfConsistent F`` and ``General.LoadRho T`` (remember that to write
a converged charge density from CONQUEST you set ``IO.DumpChargeDensity T``).
The k-points required can be specified as lines of points in k-space;
setting ``Diag.KspaceLines T`` enables this (replacing the usual MP mesh), while the number of lines
(e.g. Gamma to L; L to X; would be two lines) is set with ``Diag.NumKptLines``
and the number of points along a line with ``Diag.NumKpts``.  The k-point lines
themselves are set with a block labelled ``Diag.KpointLines`` which should have
two entries (starting and finishing k-points) for each k-point line.
(In constructing the k-point list, CONQUEST will automatically remove any duplicate
points, so that the output can be plotted smoothly.)  So to create
a bandstructure from X-:math:`\Gamma`-L-X (3 lines: X-:math:`\Gamma`; :math:`\Gamma`-L;
L-X) with 11 points in each line, you would use the following input:

::

   Diag.KspaceLines T
   Diag.NumKptLines 3
   Diag.NumKpts 11
   %block Diag.KpointLines
   0.5 0.0 0.0
   0.0 0.0 0.0
   0.0 0.0 0.0
   0.5 0.5 0.5
   0.5 0.5 0.5
   0.5 0.0 0.0
   %endblock

After running CONQUEST, setting ``Process.Job bst`` and running the post-processing
will read the resulting
``eigenvalues.dat`` file, and produce a file ``BandStructure.dat``.  The x-axis will
be the k-point index by default, but specifying ``Process.BandStrucAxis`` (taking
value ``n`` for index, ``x``, ``y`` or ``z`` for a single direction in k-space,
or ``a`` to give all k-point coordinates) will allow you to control this.  Limits
on the energies to select the bands produced can be set
with ``Process.min_DOS_E`` and ``Process.max_DOS_E``.

Go to :ref:`top <post-proc>`.

.. _pp_berry:

Berry-phase polarisation and Born effective charges
+++++++++++++++++++++++++++++++++++++++++++++++++++

``PostProcessCQ`` can calculate the macroscopic polarisation of an
insulator from the Berry phase of the occupied Bloch states on strings
of k-points (the method of King-Smith and Vanderbilt
:cite:`pp-KingSmith:1993aa`), and from several such calculations the
change of polarisation between structures, the mode effective charge of
a distortion and the Born effective charge (BEC) tensors.  Unlike the
Resta approach in CONQUEST itself (see :ref:`es_pol`), which needs a
large cell and :math:`\Gamma`-point sampling, this works with the
primitive cell and a Monkhorst-Pack mesh.

The cell may be general (non-orthogonal): lattice vectors
:math:`\mathbf{a}_\alpha` with reciprocal vectors :math:`\mathbf{b}_\alpha`
(:math:`\mathbf{a}_\alpha\cdot\mathbf{b}_\beta = 2\pi\delta_{\alpha\beta}`).
The polarisation is the Cartesian vector

.. math::
   \mathbf{P} = \frac{e}{\Omega}\sum_\alpha \pi_\alpha \mathbf{a}_\alpha, \qquad
   \pi_\alpha = -f \frac{\bar{\phi}_\alpha}{2\pi} + \sum_\kappa Z_\kappa s_{\kappa\alpha}, \qquad
   \phi_\alpha(\mathbf{k}_\perp) = -\mathrm{Im}\ln \prod_{j=0}^{J-1}
   \det \langle u_{m\mathbf{k}_j} \vert u_{n\mathbf{k}_{j+1}} \rangle

where :math:`\pi_\alpha` is the reduced polarisation along
:math:`\mathbf{a}_\alpha` (units of e), :math:`s_{\kappa\alpha}` are the
fractional coordinates of the ions, :math:`f` is 2 without spin
polarisation (1 per spin channel otherwise), the product runs over the
:math:`J` k-points of a string along :math:`\mathbf{b}_\alpha`, and
:math:`\bar{\phi}_\alpha` is the average over the strings.  The ionic part
equals :math:`\frac{e}{\Omega}\sum_\kappa Z_\kappa \mathbf{r}_\kappa`.  For
an orthorhombic cell with the lattice vectors along x, y and z,
:math:`P_\alpha = e\pi_\alpha a_\alpha/\Omega` is the Cartesian component
:math:`\alpha`.  The overlaps are calculated on the real-space
integration grid (points :math:`\sum_i (n_i/N_i)\mathbf{a}_i`) from the
wavefunction coefficients written by CONQUEST.  The polarisation is
defined only modulo the quanta :math:`e\mathbf{a}_\alpha/\Omega`, and
only *differences* between structures with the same cell are physical.

**Limitations:** insulators (the number of bands
below the Fermi level must be the same at every k-point); PAO basis sets
(not blips; tested with primitive PAOs only, not yet with MSSFs);
collinear spin.  (Of the other ``PostProcessCQ`` jobs, coordinate
conversion, charge density, band densities and STM still assume an
orthorhombic cell along x, y and z, and stop for any other cell.)

**The CONQUEST run** must be a static diagonalisation on a
Monkhorst-Pack mesh (``Diag.MPMesh T``) that writes the coefficients of
all occupied bands.  Use the list form of the wavefunction output, with
``N_occ`` the number of occupied bands (half the number of valence
electrons without spin):

::

   AtomMove.TypeOfRun static
   DM.SolutionMethod diagon
   Diag.MPMesh T
   Diag.GammaCentred T
   Diag.MPMeshX 4
   Diag.MPMeshY 4
   Diag.MPMeshZ 4
   IO.outputWF T
   IO.maxnoWF N_occ
   %block WaveFunctionsOut
   1
   2
   ...
   N_occ
   %endblock

Converge the SCF tightly (e.g. ``minE.SCTolerance 1e-8``); the
polarisation converges with the number of k-points along each string,
which should be checked.  The mesh may be reduced by time reversal (as
CONQUEST does): the missing points are reconstructed.

Polarisation of one structure
-----------------------------

Set ``Process.Job pol`` and run ``PostProcessCQ`` in the directory of
the CONQUEST run (it needs ``Conquest_input``, the coordinates, the ion
files, ``eigenvalues.dat``, ``hilbert_make_blk.dat`` or
``raster_make_blk.dat`` and ``ProcessNNNNNNNWF.dat``).  For each
lattice direction :math:`\alpha` it prints the phase of every string and
the electronic, ionic and total contributions
:math:`e\pi_\alpha\vert\mathbf{a}_\alpha\vert/\Omega` (in
e/bohr\ :sup:`2`, C/m\ :sup:`2` and :math:`\mu`\ C/cm\ :sup:`2`), the
quantum, and the total reduced modulo the quantum.  When all three
directions are computed it also prints the reduced polarisation
:math:`\pi_\alpha` and the Cartesian vector :math:`\mathbf{P}`
(electronic, ionic, total, and with each :math:`\pi_\alpha` reduced to
:math:`[-1/2,1/2)`).  For a non-orthorhombic cell the Cartesian vector
needs all three directions.  The string phases and the lattice are written
to ``BerryPolarisation.dat`` for the jobs below.

::

   Process.BerryDirection int (default: 0, all three; 1, 2 or 3 for strings along b_1, b_2 or b_3)
   Process.BerryNumOccupied int (default: 0, count bands below Ef)
   Process.BerryNumOccupiedDown int (default: Process.BerryNumOccupied)
   Process.BerryFile string (default: BerryPolarisation.dat)
   Process.BerryTableMB real (default: 4000; memory for storing PAOs on the grid)

Polarisation change and mode effective charge
---------------------------------------------

With ``Process.Job dpo``, ``PostProcessCQ`` reads the data files of the
structures listed (one directory per line, the reference first) in the
block ``Process.PolarisationRuns`` and accumulates the change of
polarisation from each structure to the next, taking the change of each
string's phase on the branch nearest zero.  For a large distortion,
list intermediate structures (e.g. :math:`\lambda = 0, 0.25, \ldots, 1`)
so that each step stays well inside half a quantum; a warning is given
when it does not.  All structures must have the same cell, atoms and
k-point mesh.  The ionic part uses minimum-image displacements.  The
change is reported in Cartesian components (for a non-orthorhombic cell
also as reduced changes along each lattice vector).  From
the total change :math:`\Delta\mathbf{P}` and displacement
:math:`\Delta\mathbf{u}` the mode effective charge is

.. math::
   Z^*_{mode,\alpha} = \frac{\Omega}{e}\frac{\Delta P_\alpha}{\vert\Delta\mathbf{u}\vert}, \qquad
   \vert\Delta\mathbf{u}\vert = \Big(\sum_\kappa \vert \Delta\mathbf{u}_\kappa\vert^2\Big)^{1/2}

in units of e.  One collective distortion gives three numbers and cannot
determine the Born effective charges of the individual atoms.

::

   %block Process.PolarisationRuns
   ref
   lambda_0.5
   lambda_1.0
   %endblock

Born effective charges
----------------------

With ``Process.Job bec``, the runs listed in
``Process.PolarisationRuns`` (the undisplaced reference first) must each
displace one Cartesian coordinate (x, y or z, also in a non-orthogonal
cell) of one atom; the atom and direction
are found from the coordinates.  For each atom and direction the slope
:math:`\partial P_\alpha/\partial u_{\kappa\beta}` is the least-squares
fit through the origin, which is the central difference for a
:math:`\pm\delta` pair, and

.. math::
   Z^*_{\kappa,\alpha\beta} = \frac{\Omega}{e}\frac{\partial P_\alpha}{\partial u_{\kappa\beta}}

includes the ionic charge.  Runs that move more than one coordinate are
rejected with an explanation.  When every atom has been displaced along
x, y and z, the acoustic sum rule :math:`\sum_\kappa Z^*_\kappa` is
reported, and the tensors are written to ``BEC_tensors.json`` (raw and
ASR-corrected, :math:`Z^* - \frac{1}{N}\sum_\kappa Z^*_\kappa`) and
``BEC_extended.xyz`` (extended XYZ with ``born_effective_charges:R:9`` in
row-major order, rows = polarisation, columns = displacement, as used
for SevenNet-Polar training data); the tensors are Cartesian and the
lattice is written as the full vectors :math:`\mathbf{a}_1,
\mathbf{a}_2, \mathbf{a}_3`.

::

   Process.BECDispTolerance real (default: 1e-5 bohr; smaller changes are ignored)
   Process.BECApplyASR boolean (default: F; ASR-corrected tensors in BEC_extended.xyz)

The script ``tools/PostProcessing/make_bec_displacements.py`` creates
the displaced run directories from a reference directory (displacements
along the Cartesian axes, converted to fractional coordinates with the
inverse lattice when the coordinates are fractional), sets
``Process.Job pol`` in each, and writes a ``Conquest_input`` with the
``Process.PolarisationRuns`` block for the final step:

::

   python3 make_bec_displacements.py ref_dir bec_dir --delta 0.02
   # run Conquest, then PostProcessCQ, in bec_dir/ref and every bec_dir/a*
   cd bec_dir; PostProcessCQ

A displacement of 0.01-0.02 bohr is usually suitable; check the
convergence of the k-point mesh and of the SCF.

Go to :ref:`top <post-proc>`.

.. bibliography:: references.bib
    :cited:
    :labelprefix: PP
    :keyprefix: pp-
    :style: unsrt
