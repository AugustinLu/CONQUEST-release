.. _elec_struc:

====================
Electronic Structure
====================

CONQUEST can be used to produce a wide variety of information on the electronic
structure of different systems, including: density of states (DOS) and atom-projected
DOS (or pDOS); band-resolved charge density; band structure; and electronic
polarisation.  Many of these are produced with the :ref:`post-processing <post-proc>`
code using a :ref:`converged charge density <es_conv>`.  All of these (at present)
require the exact diagonalisation approach to the
ground state; linear scaling solutions are not possible.

.. _es_conv:

Converged charge density
------------------------

In most cases (except :ref:`polarisation <es_pol>`) the data required is produced
by a *non-self-consistent* calculation which reads in a well-converged charge density.
The convergence is mainly with respect to :ref:`Brillouin zone sampling <gs_diag_bz>`,
but also self-consistency (a tight tolerance should be used).  The basic procedure
is:

  1. Perform a well-converged calculation, writing out charge density (ensure that
     the Brillouin zone is well sampled, the SCF tolerance is tight (``minE.SCTolerance``)
     and that the flag ``IO.DumpChargeDensity T`` is set)
  2. Perform a non-self-consistent calculation for the quantity desired
     (set ``minE.SelfConsistent F`` and ``General.LoadRho T`` to read and fix the charge density)
     using an appropriate Brillouin zone sampling
  3. Run the appropriate :ref:`post-processing <post-proc>` to generate the data

However, note that the charge density often converges much faster with respect to
Brillouin zone sampling than the detailed electronic structure, so the use of a
non-self-consistent calculation is more efficient.  Often it is most efficient and
accurate to use a very high density k-mesh for the final, non-SCF calculation, but
a lower density k-mesh to generate the charge density (which converges faster with
respect to Brillouin zone sampling than DOS and other quantities).

Go to :ref:`top <elec_struc>`.

.. _es_dos:

Density of states
-----------------

The total density of states (DOS) is generated from the file ``eigenvalues.dat`` which is
written by all diagonalisation calculations.  See :ref:`density of states <pp_DOS>` for
details on parameters which can be set.

The atom-projected DOS resolves the total DOS into contributions from individual atoms
using the pseudo-atomic orbitals, and can further decompose this into *l*-resolved or
*lm*-resolved densities of states.  It requires the wave-function coefficients, which will be generated
by setting ``IO.write_proj_DOS T``; further analysis is performed in :ref:`post-processing <pp_pDOS>`.

Go to :ref:`top <elec_struc>`.

.. _es_band_struc:

Band structure
--------------

The band structure along a series of lines in reciprocal space can be generated.
See :ref:`post-processing <post-proc>` for more details.

Go to :ref:`top <elec_struc>`.

.. _es_band_dens:

Band-resolved densities
-----------------------

A band-resolved density is the quantity :math:`\mid \psi_n(\mathbf{r}) \mid^2`
for the :math:`n^{\mathrm{th}}` Kohn-Sham eigenstate (we plot density because
the eigenstates are in general complex).  It requires wavefunction coefficients
which are generated by setting ``IO.outputWF T``.  Full details are found in
the :ref:`band density <pp_band_dens>` section of the :ref:`post-processing <post-proc>`
part of the manual.

Go to :ref:`top <elec_struc>`.

.. _es_pol:

Electronic Polarisation
-----------------------

The electronic polarisation (the response of a material to an
external electric field) can be calculated using the approach
of Resta :cite:`es-Resta:1992aa` by setting the tag ``General.CalcPol T``.
The direction in which polarisation is found is set using the tag
``General.PolDir`` (choosing 1-3 gives x, y or z, respectively, while
choosing 0 gives all three directions, though this is normally not
recommended).

The Resta approach is a version of the modern theory of polarisation (MTP)
(perhaps better known in the method of King-Smith and Vanderbilt :cite:`es-KingSmith:1993aa`)
where the polarisation is found as:

.. math::
   \mathbf{P} = -\frac{e\mathrm{L}}{\pi V}\mathrm{Im}\mathrm{ln}\mathrm{det}\mathbf{S}\\
   \mathrm{S}_{mn} = \langle \psi_{m} \vert \exp{i2\pi \mathbf{r}}/L\vert\psi_{n} \rangle

where :math:`\mathrm{L}` is a simulation cell length along an appropriate direction
and :math:`V` is the simulation cell volume.  This approach is **only valid** in the large
simulation cell limit, with :math:`\Gamma` point sampling (e.g. for BaTiO3, a minimum of
3x3x3 formula units is needed, though this is perhaps a little too small).

As with all calculations in the MTP,
the only valid physical quantity is a *change* of polarisation between two configurations.
A very common quantity to calculate is the Born effective charge (BEC), which is defined
as :math:`Z^{*}_{k,\alpha\beta} = V\partial P_{\alpha}/\partial u_{k,\beta}` for species
:math:`k` and Cartesian directions :math:`\alpha` and :math:`\beta`. It is most easily
calculated by finding the change in polarisation as one atom (or one set of atoms in
a sublattice) is moved a small amount.

Go to :ref:`top <elec_struc>`.

.. bibliography:: references.bib
    :cited:
    :labelprefix: ES
    :keyprefix: es-
    :style: unsrt

Go to :ref:`top <basissets>`.
