! -*- mode: F90; mode: font-lock -*-
! ------------------------------------------------------------------------------
! $Id$
! ------------------------------------------------------------------------------
! Module global_module
! ------------------------------------------------------------------------------
! Code area 9: general
! ------------------------------------------------------------------------------

!!****h* Conquest/global_module *
!!  NAME
!!   global_module
!!  PURPOSE
!!   Holds various global variables
!!  USES
!!   datatypes
!!  AUTHOR
!!   D.R.Bowler
!!  CREATION DATE
!!   24/11/99
!!  MODIFICATION HISTORY
!!   30/05/2001 dave
!!    ROBODoc header, removed unnecessary variables
!!   18/03/2002 dave
!!    Added RCS Id and Log tags and static tag for object file id
!!   13:49, 10/02/2003 drb 
!!    Added flags for minimisation control
!!   10:58, 2003/06/10 dave
!!    Added new flags for different options and new atomic coordinate variables
!!   12:19, 29/08/2003 drb 
!!    Added flag_move_atom
!!   13:33, 22/09/2003 drb 
!!    Added flags to allow separate testing of S-Pulay and phi-Pulay forces
!!   08:31, 2003/10/01 dave
!!    Changed flag_vary_blips to flag_vary_basis
!!   14:56, 02/05/2005 dave 
!!    Added global ne_in_cell variable for total electron number in cell
!!   09:11, 11/05/2005 dave 
!!    Added max L iterations parameter
!!   2006/09/04 08:06 dave
!!    Dynamic allocation implemented for final variables
!!   2006/10/10 10:05 ast
!!    Flag for selecting functional and string for its description
!!   2007/03/23 17:16 dave
!!    Added new variables for automatic partitioning
!!   2007/04/18 17:26 dave
!!    Added flag for block assignment
!!   2008/02/01 03:43 dave
!!    Added output unit (output to file rather than stdout)
!!   12:19, 14/02/2008 drb 
!!    Added flag for Pulay relaxation algorithm
!!   2008/07/16 ast
!!    New iprint levels for timing 
!!   2009/07/24 16:41 dave
!!    Added new flag for global or per atom tolerances
!!   2011/03/30 18:59 M.Arita
!!    Added new flag for for P.C.C.
!!   2011/04/01 L.Tong
!!    Added flag_spin_polarisation as a switch for spin polarised calculation
!!    Added flag functional_lsda_pw92 for LSDA
!!   2011/07/26 L.Tong
!!    Added flag_fix_spin_population as switch for fixing spin population
!!   Friday, 2011/08/05 L.Tong
!!    Added initial (fixed) electron numbers for spin up and down
!!    channels, used when flag_fix_spin_population is true
!!    Moved all new variables for spin polarisation calculations together
!!   2011/09/29 14:51 M. Arita
!!    Added new flags for DFT-D2
!!   2011/07/21 16:35 dave
!!    Flags for cDFT
!!   2011/12/12 17:26 dave
!!    Flag for analytic blip integrals
!!   2012/03/07 L.Tong
!!    Added some more flags for spin polarisation, and uses numbers module
!!   2012/03/27 L.Tong
!!   - Added variable nspin
!!   - Added variable ne_spin_in_cell(nspin). This replaces
!!     ne_up_in_cell and ne_dn_in_dell
!!   - Added variable spin_factor
!!   - Default values are:
!!     nspin = 1
!!     spin_factor = two
!!   - removed now obsolete flag: flag_spin_polarisation
!!   2012/05/29 L.Tong
!!   - removed functional_lsda_pw92, now redundant. Just use
!!     functional_lda_pw92 for PW92 LDA.
!!   2012/06/24 L.Tong
!!   - Added flag flag_dump_L for controlling if L is to be dumped
!!   2013/01/30 10:30 dave
!!   - Adding deltaSCF variables (with U. Terranova)
!!   2013/07/01 M.Arita
!!   - Added flags and parameters for the efficient MD scheme
!!   2013/08/20 M.Arita
!!   - Added flags and variables for matrix reconstruction
!!   2013/12/02 M.Arita
!!   - Added flags and variables for XL-BOMD
!!   2014/01/17 lat 
!!    Added new area and flag for EXX 
!!   2014/09/20 lat
!!    Added flags for PBE0, Xalpha and Hartree-Fock functional
!!   2014/10/03 lat
!!    Added parameters for SCF control of EXX and iprint_exx
!!   2015/05/11 L.Truflandier
!!   - Added optional total spin magnetization ne_magn_in_cell
!!   2015/05/29
!!    Wavefunction output flags (COR and dave)
!!   2015/06/19
!!    FIRE implmementation (SA, COR, dave)
!!   2015/07/08 08:03 dave
!!    DOS and k-point by k-point wavefunction output (for STM)
!!   2015/11/09 08:23 dave (with TM, NW of Mizuho)
!!    Added neutral atom flag
!!   2016/02/16 JKS
!!    Added Wu-Cohen XC functional  (PRB 73, 235116  (2006) )
!!   2016/08/01 17:30 nakata
!!    Introduced atomf
!!   2016/08/09 21:30 nakata
!!    Added parameters for Contracted SFs and multi-site SFs
!!   2017/02/23 dave
!!    - Changing location of diagon flag from DiagModule to global and name to flag_diagonalisation
!!   2017/04/05 18:00 nakata
!!    Added flag_readAtomicSpin to initialise spin
!!   2017/08/29 jack baker & dave
!!    Adding variables for cell optimisation
!!   2017/10/20 09:19 dave
!!    Moved fire variables to Integrators_module
!!   2017/11/13 18:15 nakata
!!    Added a flag to normalise pDOS
!!   2017/12/05 09:59 dave with TM & NW (MIZUHO)
!!    Added new function type - NA projector function (napf)
!!   2018/04/25 10:00 zamaan
!!    Added target attribute to rcellx, x_atom_cell etc.
!!   2018/05/17 12:51 dave with Ayako Nakata
!!    Changed flag_readAtomicSpin to flag_InitialAtomicSpin (more descriptive) and moved to density_module
!!   2018/09/19 18:30 nakata
!!    Added a flag for orbital angular momentum resolved PDOS
!!   2018/10/22 14:25 dave & jsb
!!    Adding (l,m)-projection for PDOS
!!   2019/02/28 zamaan
!!    Added enthalpy and stress tolerances for cell optimisation
!!   2019/03/28 zamaan
!!    Added flag_stress and flag_full_stress
!!   2019/05/08 zamaan
!!    Added flag_atomic_stress and atomic_stress for atomic contributions to 
!!    stress and heat flux
!!   2019/05/21 zamaan
!!    Added RNG seed
!!   2019/11/14 tsuyoshi
!!    Removed n_proc_old and glob2node_old
!!   2019/11/18 tsuyoshi
!!    Removed flag_MDold
!!   2019/11/18 14:37 dave
!!    Added flag_variable_cell
!!   2020/07/27 tsuyoshi
!!    Added atom_vels 
!!   2021/07/19 15:00 dave
!!    Removed flag for wavefunction output by k-point
!!   2022/10/28 15:56 lionel
!!    Added ASE output unit
!!   2023/01/12 17:11 dave
!!    Variables for polarisation calculation
!!   2024/05/29 17:40 nakata
!!    Added DFT+U flag
!!   2026/07/29 lu
!!    Added full direct/inverse/reciprocal lattice and exact triclinic MIC
!!   2026/07/29 lu
!!    Defined inverse output explicitly for singular lattice matrices
!!   2026/07/29 lu
!!    Added bounded-search diagnostics for exact minimum-image calculations
!!  SOURCE
!!
module global_module

  ! Module usage
  use datatypes
  use numbers

  implicit none

  integer :: iprint                 ! Level of output
  integer :: io_lun                 ! Conquest output unit
  !
  integer :: io_ase                 ! ASE output unit  
  logical :: write_ase              ! Whether we write ASE ouptput or not
  character(len=80) :: ase_file = 'Conquest_out_ase' ! ASE file output
  !
  integer, allocatable, dimension(:) :: id_glob      ! global label of atom in sim cell (CC)
  integer, allocatable, dimension(:) :: id_glob_inv  ! gives global number for a CC atom
  integer, dimension(:), allocatable, target :: species_glob ! gives species 
  integer :: numprocs               ! number of processors
  real(double), target, dimension(3,3) :: lat_vec
  real(double), target, dimension(3,3) :: lat_vec_inv
  real(double), target, dimension(3,3) :: recip_lat_vec
  real(double), target :: cell_vol
  real(double), dimension(3), target :: cell_vec_len
  integer, parameter :: mic_count_kind = selected_int_kind(18)
  integer(mic_count_kind), parameter :: mic_warning_threshold = 1000_mic_count_kind
  integer(mic_count_kind), save :: mic_max_candidate_count = 0_mic_count_kind
  logical, save :: mic_search_warning_issued = .false.
  real(double), allocatable, dimension(:), target :: x_atom_cell ! position of atom in sim cell (CC)
  real(double), allocatable, dimension(:), target :: y_atom_cell
  real(double), allocatable, dimension(:), target :: z_atom_cell
  integer,      allocatable, dimension(:), target :: coord_to_glob
  integer      :: ni_in_cell ! Atoms in cell
  real(double) :: ne_in_cell ! Electrons in cell
  ! atom_coord : Use global labelling, in the future this array should
  ! be used instead of x, y, z_atom_cell. by T. Miyazaki
  real(double), dimension(:,:), allocatable, target :: atom_coord ! Atomic coordinates
  real(double), dimension(:,:), allocatable, target :: atom_vels  ! Atomic velocities 
  integer,      dimension(:,:), allocatable :: sorted_coord ! Atom IDs of atoms sorted according to x, y, z coords
  logical,      dimension(:,:), allocatable :: flag_move_atom  ! Move atoms ?
  integer,      dimension(:),   allocatable :: flag_cdft_atom
  logical :: restart_DM, restart_rho, restart_T, restart_X
  logical :: flag_DM_converged

  integer :: global_maxatomspart ! Maximum atoms per partition, if exceeded, triggers partitioning refinement

  integer :: rng_seed

  integer :: load_balance
  logical :: many_processors ! Selects appropriate algorithm for partitioning

  character(len=20), save :: runtype ! What type of run is it ?

  logical :: flag_stress   ! Compute the stress tensor?
  logical :: flag_full_stress ! Compute the off-diagonal elements?
  logical :: flag_atomic_stress ! Compute atomic contributions to stress?
  logical :: flag_heat_flux ! Compute heat flux during MD?

  ! Atomic contributions to total stress
  ! I would rather not put this in global module, but it is required by enough
  ! different force computing modules that it's impossible to put it in a more
  ! sensible file without circular dependencies - zamaan
  real(double), dimension(:,:,:), allocatable :: atomic_stress
  real(double), dimension(3,3)                :: non_atomic_stress

  logical :: flag_opt_cell ! optimize the simulation cell?
  logical :: flag_variable_cell ! Global indicator of whether cell will change
  integer :: optcell_method ! method for cell optimiisation 1 = cell, fixed fractional coords, 2 = nested loop cell + geometry optimisation, 3 = single vector full optimisation
  ! specify sim cell dims/ratios of dims to be held constant.
  character(len=20), save :: cell_constraint_flag
  ! Termination condition to exit cell_cg_run
  real(double) :: cell_en_tol, cell_stress_tol


  ! Logical flags controlling run
  logical :: flag_vary_basis, flag_self_consistent, flag_residual_done
  ! Logical flags controlling preconditioning
  logical :: flag_precondition_blips
  logical :: flag_analytic_blip_int
  ! Logical flag controlling atomic coordinate format
  logical :: flag_fractional_atomic_coords
  logical :: flag_old_partitions
  logical :: flag_read_blocks ! Do we read make_blk.prt or raster ?
  logical :: flag_test_forces
  logical :: flag_reset_dens_on_atom_move
  logical :: flag_continue_on_SC_fail
  logical :: flag_SCconverged
  logical :: UseGemm
  logical :: flag_pulay_simpleStep
  logical :: flag_global_tolerance
  logical :: flag_Becke_weights
  logical :: flag_Becke_atomic_radii
  logical :: flag_perform_cDFT
  logical :: flag_mix_L_SC_min
  logical :: flag_onsite_blip_ana
  logical :: flag_read_velocity   ! 16/06/2010 TM
  logical :: flag_quench_MD       ! 25/06/2010 TM
  logical :: flag_fire_qMD        ! 2014/07/31 SA
  real(double) :: temp_ion        ! 25/06/2010 TM

  ! How should blocks be assigned ? See block_module.f90
  integer :: flag_assign_blocks

  ! Number of L iterations
  integer :: max_L_iterations

  ! Numerical flag choosing basis sets
  integer :: flag_basis_set
  integer, parameter :: blips = 1
  integer, parameter :: PAOS  = 2

  ! Switch for variation of blips in get_support_gradient
  integer :: WhichPulay
  integer, parameter :: PhiPulay  = 1
  integer, parameter :: SPulay    = 2
  integer, parameter :: BothPulay = 3 

  ! What are the local functions ? 
  integer, parameter :: sf   = 1 ! Support functions
  integer, parameter :: nlpf = 2 ! Projector functions
  integer, parameter :: paof = 3 ! Pseudo-atomic orbitals
  integer, parameter :: dens = 4 ! Atomic charge density
  integer, parameter :: napf = 5 ! Neutral atom projector functions
  integer            :: atomf    ! 1(=sf) for blips and primitive paos, 3(=paof) for contracted paos

  ! Define areas of the code
  integer, parameter :: n_areas        = 13
  integer, parameter :: area_init      = 1
  integer, parameter :: area_matrices  = 2
  integer, parameter :: area_ops       = 3
  integer, parameter :: area_DM        = 4 
  integer, parameter :: area_SC        = 5
  integer, parameter :: area_minE      = 6
  integer, parameter :: area_moveatoms = 7
  integer, parameter :: area_index     = 8
  integer, parameter :: area_general   = 9
  integer, parameter :: area_pseudo    = 10
  integer, parameter :: area_basis     = 11
  integer, parameter :: area_integn    = 12
  integer, parameter :: area_exx       = 13
  integer :: iprint_init, iprint_mat,     iprint_ops,   iprint_DM,    &
             iprint_SC,   iprint_minE,    iprint_MD,    iprint_index, &
             iprint_gen,  iprint_pseudo,  iprint_basis, iprint_intgn, &
             iprint_time, iprint_MDdebug, iprint_exx

  integer, parameter :: IPRINT_TIME_THRES0 = 0  ! Always print
  integer, parameter :: IPRINT_TIME_THRES1 = 2  ! Important local timers
  integer, parameter :: IPRINT_TIME_THRES2 = 4  ! Not that important
  integer, parameter :: IPRINT_TIME_THRES3 = 6  ! For special purposes

  integer :: min_layer ! Layer of minimisation algorithm (from 0 to -n)
  ! For P.C.C.
  logical :: flag_pcc_global = .false.

  !! For Spin polarised calculations (L.Tong)
  ! default to spin nonpolarised calculation
  ! number of spin channels
  integer      :: nspin = 1
  real(double) :: spin_factor = two
  ! Logical flag determine if spin populations are fixed (fixed magnetic moment) 
  logical      :: flag_fix_spin_population = .false.
  ! fixed electron numbers for different spin channels. This is used
  ! even for spin non-polarised case
  real(double), dimension(2) :: ne_spin_in_cell ! 1 = up, 2 = down
  real(double)               :: ne_magn_in_cell

  ! For DFT-D2
  logical :: flag_dft_d2
  logical :: flag_SCconverged_D2 = .false.
  logical :: flag_only_dispersion

  ! For vdwDFT
  logical :: flag_vdWDFT          ! selector for turning on vdW energy correction
  integer :: vdW_LDA_functional   ! selector for LDA functional

  ! DeltaSCF
  logical :: flag_DeltaSCF
  logical :: flag_excite = .false.
  logical :: flag_local_excitation
  integer :: dscf_source_level, dscf_target_level, dscf_source_spin, &
       dscf_target_spin, dscf_source_nfold, dscf_target_nfold, &
       dscf_homo_limit, dscf_lumo_limit
  real(double) :: dscf_HOMO_thresh, dscf_LUMO_thresh

  ! For EXX
  logical      :: flag_exx      = .false. ! switch on/off EXX
  integer      :: exx_scf       = 0       ! method used during the SCF using hybrid functional or Hartree-Fock
  real(double) :: exx_alpha     = zero    ! mixing factor for hybrid Exc
  real(double) :: exx_cutoff    = 100.0_double ! cutoff for screening (experimental) 
 
  integer      :: exx_niter     = 1       ! for EXX control during SCF
  integer      :: exx_siter     = 1       ! for EXX control during SCF
  real(double) :: exx_pulay_r0  = zero    ! get the R0 pulay residual for control
  real(double) :: exx_scf_ratio = zero    ! for EXX control during SCF
  real(double) :: exx_scf_tol   = zero    ! for EXX control during SCF

  ! pre-defined grid spacing in Bohr
  real(double), parameter :: exx_hgrid_coarse = 0.60_double
  real(double), parameter :: exx_hgrid_medium = 0.50_double
  real(double), parameter :: exx_hgrid_fine   = 0.20_double

  ! Flag to control if matrix L is dumped to files
  logical :: flag_dump_L
  logical :: flag_DumpMatrices

  ! Hold an old relation between global & partition labels
  integer,allocatable :: id_glob_old(:),id_glob_inv_old(:)

  ! For MD
  logical :: flag_LmatrixReuse
  logical :: flag_TmatrixReuse
  logical :: flag_SkipEarlyDM
  logical :: flag_MDcontinue
  logical :: flag_MDdebug
  logical :: flag_thermoDebug
  logical :: flag_baroDebug
  logical :: flag_FixCOM 
  integer :: McWFreq
  integer :: MDinit_step  
  !ORI real(double),parameter   :: shift_in_bohr = 1.0E-03_double
  real(double),parameter   :: shift_in_bohr = 1.0E-06_double
  ! Table showing atoms (global) in nodes
  integer,allocatable :: glob2node(:)        ! size: ni_in_cell
  ! Displacement of atoms from a previous step
  real(double),allocatable :: atom_coord_diff(:,:)
  ! XL-BOMD
  logical :: flag_XLBOMD
  logical :: flag_propagateX,flag_propagateL
  logical :: flag_dissipation
  character(20) :: integratorXL
  
  ! Wavefunction output
  logical :: flag_out_wf                        !output WFs?
  integer,allocatable,dimension(:)::out_wf      !which bands to output  
  integer::max_wf                               !total no of bands
  logical :: wf_self_con                        !flag to select output at the end of SCF cycle
  real(double) :: E_wf_min, E_wf_max            ! Limits for energy range
  logical :: flag_wf_range_Ef                   ! Is the energy range relative to Ef (T) or absolute (F)

  ! This is in the WF output section as I introduced it for WF output, but
  ! it more properly applies to matrices (specifically how many temporary matrices we can store)
  integer :: mx_temp_matrices                   ! Defaults to 100; used in mult_module (immi)
  
  ! DOS output (NB Maybe move these into DiagModule and revisit names)
  logical :: flag_write_projected_DOS, flag_normalise_pDOS, flag_pDOS_angmom, flag_pDOS_lm
  real(double) :: E_DOS_min, E_DOS_max, sigma_DOS
  integer :: n_DOS

  ! Neutral atom potential
  logical :: flag_neutral_atom

  ! Contracted SF
  logical :: flag_SpinDependentSF
  integer :: nspin_SF
  logical :: flag_SFcoeffReuse

  ! Multisite
  logical :: flag_Multisite
  logical :: flag_LFD

  ! diagonalise or linear scaling
  logical :: flag_diagonalisation

  ! Polarisation
  logical :: flag_calc_pol, flag_do_pol_calc
  integer, dimension(3) :: mat_polX_re, mat_polX_im
  integer, dimension(3) :: mat_polX_re_atomf, mat_polX_im_atomf
  complex(double_cplx), dimension(:,:,:,:), allocatable, target :: polS
  integer :: i_pol_dir_st, i_pol_dir_end ! Either 1,1 or 1,3
  integer, dimension(3) :: i_pol_dir ! Either n,0,0 or 1,2,3

  ! DFT+U
  logical :: flag_DFTplusU, flag_first_diag, flag_write_occ_mat
  real(double), dimension(:,:,:,:), allocatable :: occ_mat ! Occupation matrix (m,m,primary atom, spin)
  real(double), dimension(:,:,:,:), allocatable :: occ_mat_glob ! Occupation matrix (m,m,global atom, spin)

  ! Density matrix Lagrange multiplier for correct electron number (needed for forces and stress)
  real(double), dimension(2) :: mu_DMM ! Allow for spin

contains

  logical function cell_requires_full_stress()
    ! The stress tensor is expressed in Cartesian coordinates.  Whenever the
    ! lattice is not represented by three positive, Cartesian-aligned vectors,
    ! shear components cannot safely be treated as optional: a skewed or
    ! rotated cell can couple them into cell dynamics and relaxation.
    real(double) :: axis_aligned_lattice(3,3), scale, tolerance
    integer :: i

    axis_aligned_lattice = zero
    do i = 1, 3
       axis_aligned_lattice(i,i) = cell_vec_len(i)
    end do
    scale = max(one, maxval(cell_vec_len))
    tolerance = 128.0_double*epsilon(one)*scale
    cell_requires_full_stress = &
         maxval(abs(lat_vec-axis_aligned_lattice)) > tolerance
  end function cell_requires_full_stress

  logical function cell_has_nonorthogonal_vectors()
    real(double) :: scale, tolerance
    integer :: i, j

    cell_has_nonorthogonal_vectors = .false.
    tolerance = 128.0_double*epsilon(one)
    do i = 1, 2
       do j = i + 1, 3
          scale = cell_vec_len(i)*cell_vec_len(j)
          if (abs(dot_product(lat_vec(:,i),lat_vec(:,j))) > &
               tolerance*scale) then
             cell_has_nonorthogonal_vectors = .true.
             return
          end if
       end do
    end do
  end function cell_has_nonorthogonal_vectors

  real(double) function reciprocal_lattice_norm(index)
    ! Norm of reciprocal basis vector index without the conventional 2*pi.
    ! This is the inverse spacing of direct-lattice planes normal to that
    ! reciprocal vector.
    integer, intent(in) :: index

    reciprocal_lattice_norm = &
         sqrt(dot_product(recip_lat_vec(:,index), recip_lat_vec(:,index)))
  end function reciprocal_lattice_norm

  real(double) function point_parallelepiped_distance_sq(point, origin, edges)
    ! Exact squared distance from a Cartesian point to the closed
    ! parallelepiped origin + edges*t, 0 <= t_i <= 1.  Enumerating the 27
    ! active sets (lower/free/upper for each coordinate) makes this small
    ! convex projection deterministic without assuming orthogonal edges.
    real(double), intent(in) :: point(3), origin(3), edges(3,3)
    real(double) :: coefficients(3), candidate(3), residual(3)
    real(double) :: edge_norms(3), unit_edges(3,3)
    real(double) :: gram(3,3), gram_inverse(3,3), rhs(3)
    real(double) :: determinant, tolerance, trial_distance
    integer :: states(3), free_indices(3), n_free
    integer :: state1, state2, state3, i, j
    logical :: valid

    point_parallelepiped_distance_sq = huge(one)
    tolerance = 128.0_double*epsilon(one)
    do i = 1, 3
       edge_norms(i) = sqrt(dot_product(edges(:,i),edges(:,i)))
       if (edge_norms(i) <= tiny(one)) return
       unit_edges(:,i) = edges(:,i)/edge_norms(i)
    end do
    do state3 = -1, 1
       do state2 = -1, 1
          do state1 = -1, 1
             states = (/ state1, state2, state3 /)
             coefficients = zero
             n_free = 0
             do i = 1, 3
                if (states(i) == 1) coefficients(i) = one
                if (states(i) == 0) then
                   n_free = n_free + 1
                   free_indices(n_free) = i
                end if
             end do

             residual = point - origin - matmul(edges,coefficients)
             valid = .true.
             select case(n_free)
             case(0)
                continue
             case(1)
                i = free_indices(1)
                coefficients(i) = dot_product(unit_edges(:,i),residual) &
                     /edge_norms(i)
             case default
                gram = zero
                rhs = zero
                do i = 1, n_free
                   rhs(i) = dot_product(unit_edges(:,free_indices(i)),residual)
                   do j = 1, n_free
                      gram(i,j) = dot_product(unit_edges(:,free_indices(i)), &
                           unit_edges(:,free_indices(j)))
                   end do
                end do
                if (n_free == 2) gram(3,3) = one
                call invert_3x3(gram, gram_inverse, determinant, valid)
                if (valid) then
                   rhs(n_free+1:3) = zero
                   rhs = matmul(gram_inverse,rhs)
                   do i = 1, n_free
                      coefficients(free_indices(i)) = &
                           rhs(i)/edge_norms(free_indices(i))
                   end do
                end if
             end select

             do i = 1, n_free
                j = free_indices(i)
                if (coefficients(j) < -tolerance .or. &
                     coefficients(j) > one+tolerance) valid = .false.
                coefficients(j) = max(zero,min(one,coefficients(j)))
             end do
             if (valid) then
                candidate = origin + matmul(edges,coefficients)
                trial_distance = dot_product(point-candidate,point-candidate)
                point_parallelepiped_distance_sq = &
                     min(point_parallelepiped_distance_sq,trial_distance)
             end if
          end do
       end do
    end do
  end function point_parallelepiped_distance_sq

  subroutine invert_3x3(mat, inv_mat, det, is_valid)
    real(double), intent(in) :: mat(3,3)
    real(double), intent(out) :: inv_mat(3,3)
    real(double), intent(out) :: det
    logical, intent(out), optional :: is_valid

    inv_mat = zero
    if (present(is_valid)) is_valid = .false.
    det = mat(1,1)*(mat(2,2)*mat(3,3) - mat(2,3)*mat(3,2)) &
        - mat(1,2)*(mat(2,1)*mat(3,3) - mat(2,3)*mat(3,1)) &
        + mat(1,3)*(mat(2,1)*mat(3,2) - mat(2,2)*mat(3,1))

    if (abs(det) < 1e-12) return

    inv_mat(1,1) =  (mat(2,2)*mat(3,3) - mat(2,3)*mat(3,2)) / det
    inv_mat(1,2) = -(mat(1,2)*mat(3,3) - mat(1,3)*mat(3,2)) / det
    inv_mat(1,3) =  (mat(1,2)*mat(2,3) - mat(1,3)*mat(2,2)) / det

    inv_mat(2,1) = -(mat(2,1)*mat(3,3) - mat(2,3)*mat(3,1)) / det
    inv_mat(2,2) =  (mat(1,1)*mat(3,3) - mat(1,3)*mat(3,1)) / det
    inv_mat(2,3) = -(mat(1,1)*mat(2,3) - mat(1,3)*mat(2,1)) / det

    inv_mat(3,1) =  (mat(2,1)*mat(3,2) - mat(2,2)*mat(3,1)) / det
    inv_mat(3,2) = -(mat(1,1)*mat(3,2) - mat(1,2)*mat(3,1)) / det
    inv_mat(3,3) =  (mat(1,1)*mat(2,2) - mat(1,2)*mat(2,1)) / det
    if (present(is_valid)) is_valid = .true.
  end subroutine invert_3x3

  subroutine wrap_into_cell(x, y, z)
    real(double), intent(inout) :: x, y, z
    real(double), dimension(3) :: r, f
    r(1) = x
    r(2) = y
    r(3) = z
    f = matmul(lat_vec_inv, r)
    ! Map coordinates to [0, 1) instead of [-0.5, 0.5)
    f = f - floor(f)
    r = matmul(lat_vec, f)
    x = r(1)
    y = r(2)
    z = r(3)
  end subroutine wrap_into_cell

  subroutine mic_coords(xi, yi, zi, xj, yj, zj)
    real(double), intent(in) :: xi, yi, zi
    real(double), intent(inout) :: xj, yj, zj
    real(double), dimension(3) :: r
    r(1) = xj - xi
    r(2) = yj - yi
    r(3) = zj - zi
    ! mic_coords computes a distance vector, so it MUST use mic_vector ([-0.5, 0.5))
    call mic_vector(r)
    xj = xi + r(1)
    yj = yi + r(2)
    zj = zi + r(3)
  end subroutine mic_coords

  subroutine mic_vector(r)
    real(double), dimension(3), intent(inout) :: r
    real(double), dimension(3) :: f, shifted, best, candidate
    real(double) :: best_sq, candidate_sq, coefficient_bound, rounding_guard
    integer, dimension(3) :: nearest, lower, upper
    integer :: i, n1, n2, n3
    integer(mic_count_kind) :: candidate_count, extent_count

    ! Component-wise fractional rounding is not the Euclidean minimum-image
    ! convention for a sufficiently skewed or unreduced lattice.  Start with
    ! that inexpensive candidate, then enumerate a rigorously bounded integer
    ! box.  If |A(f-n)| <= |best|, then
    !
    !   |f_i-n_i| = |row_i(A^-1) A(f-n)|
    !             <= ||row_i(A^-1)|| |best| .
    !
    ! Consequently the bounds below contain every lattice translation that
    ! can improve on the initial candidate.  This is an exact three-
    ! dimensional closest-vector search without assuming a reduced cell.
    f = matmul(lat_vec_inv, r)
    nearest = nint(f)
    shifted = f - real(nearest, double)
    best = matmul(lat_vec, shifted)
    best_sq = dot_product(best, best)

    do i = 1, 3
       coefficient_bound = sqrt(best_sq) * &
            sqrt(dot_product(lat_vec_inv(i,:), lat_vec_inv(i,:)))
       rounding_guard = 16.0_double * epsilon(one) * &
            (one + abs(f(i)) + coefficient_bound)
       lower(i) = ceiling(f(i) - coefficient_bound - rounding_guard)
       upper(i) = floor(f(i) + coefficient_bound + rounding_guard)
    end do

    candidate_count = 1_mic_count_kind
    do i = 1, 3
       extent_count = int(upper(i), mic_count_kind) - &
            int(lower(i), mic_count_kind) + 1_mic_count_kind
       if (candidate_count > huge(candidate_count)/extent_count) then
          candidate_count = huge(candidate_count)
       else
          candidate_count = candidate_count*extent_count
       end if
    end do
    mic_max_candidate_count = max(mic_max_candidate_count, candidate_count)
    if (.not. mic_search_warning_issued .and. &
         candidate_count > mic_warning_threshold) then
       write(io_lun,'(a,i0,a)') " WARNING: exact minimum-image search has ", &
            candidate_count, " candidates; consider a reduced lattice basis"
       mic_search_warning_issued = .true.
    end if

    do n3 = lower(3), upper(3)
       do n2 = lower(2), upper(2)
          do n1 = lower(1), upper(1)
             shifted = f - real((/ n1, n2, n3 /), double)
             candidate = matmul(lat_vec, shifted)
             candidate_sq = dot_product(candidate, candidate)
             if (candidate_sq < best_sq) then
                best = candidate
                best_sq = candidate_sq
             end if
          end do
       end do
    end do
    r = best
  end subroutine mic_vector

  subroutine fractional_recip_to_cart(k)
    ! lat_vec stores direct lattice vectors as columns.  For fractional
    ! reciprocal coordinates q, k = 2*pi*A^{-T}*q.
    real(double), dimension(3), intent(inout) :: k
    k = two*pi*matmul(transpose(lat_vec_inv), k)
  end subroutine fractional_recip_to_cart

  subroutine cart_recip_to_fractional(k)
    ! Inverse of fractional_recip_to_cart: q = A^T*k/(2*pi).
    real(double), dimension(3), intent(inout) :: k
    k = matmul(transpose(lat_vec), k)/(two*pi)
  end subroutine cart_recip_to_fractional

  subroutine lattice_grid_block_origin(ibx, iby, ibz, nbx, nby, nbz, x, y, z)
    ! Cartesian origin of a real-space integration-grid block.  The lattice
    ! vectors are stored as columns of lat_vec, so a block displacement is a
    ! fractional lattice displacement, not a displacement along Cartesian axes.
    integer, intent(in) :: ibx, iby, ibz, nbx, nby, nbz
    real(double), intent(out) :: x, y, z
    real(double) :: fx, fy, fz

    fx = real(ibx, double)/real(nbx, double)
    fy = real(iby, double)/real(nby, double)
    fz = real(ibz, double)/real(nbz, double)
    x = fx*lat_vec(1,1) + fy*lat_vec(1,2) + fz*lat_vec(1,3)
    y = fx*lat_vec(2,1) + fy*lat_vec(2,2) + fz*lat_vec(2,3)
    z = fx*lat_vec(3,1) + fy*lat_vec(3,2) + fz*lat_vec(3,3)
  end subroutine lattice_grid_block_origin

  subroutine lattice_grid_point_offset(ix, iy, iz, nbx, nby, nbz, &
       nx_block, ny_block, nz_block, dx, dy, dz)
    ! Cartesian offset of a point within a real-space integration-grid block.
    integer, intent(in) :: ix, iy, iz, nbx, nby, nbz
    integer, intent(in) :: nx_block, ny_block, nz_block
    real(double), intent(out) :: dx, dy, dz
    real(double) :: fx, fy, fz

    fx = real(ix - 1, double)/real(nbx*nx_block, double)
    fy = real(iy - 1, double)/real(nby*ny_block, double)
    fz = real(iz - 1, double)/real(nbz*nz_block, double)
    dx = fx*lat_vec(1,1) + fy*lat_vec(1,2) + fz*lat_vec(1,3)
    dy = fx*lat_vec(2,1) + fy*lat_vec(2,2) + fz*lat_vec(2,3)
    dz = fx*lat_vec(3,1) + fy*lat_vec(3,2) + fz*lat_vec(3,3)
  end subroutine lattice_grid_point_offset

end module global_module
!!***
