! -----------------------------------------------------------
! Module berry
! -----------------------------------------------------------
! Code area: PostProcessCQ
! -----------------------------------------------------------

!!****h* PostProcessCQ/berry
!!  NAME
!!   berry
!!  PURPOSE
!!   Macroscopic polarisation from the Berry phase on strings of k-points
!!   (King-Smith and Vanderbilt, PRB 47, 1651 (1993)), computed from the
!!   wavefunction coefficients written by CONQUEST (Process*WF.dat), and
!!   quantities built from several such calculations:
!!
!!    Process.Job pol : polarisation of one structure; writes a data file
!!    Process.Job dpo : polarisation change along a sequence of structures
!!                      and the mode effective charge of that distortion
!!    Process.Job bec : Born effective charge tensors by finite differences
!!                      of single-atom displacements
!!
!!   Bloch phase convention (as in DiagModule and pao_to_grid): the Bloch sum
!!   of PAO mu on atom I is sum_R exp(ik.(R+tau_I)) phi_mu(r-R-tau_I), so
!!   psi_k(r) is evaluated on the real-space grid directly from the
!!   coefficients.  The overlap between neighbouring k-points on a string is
!!
!!     M_mn(k_j,k_j+1) = <u_mk_j|u_nk_j+1>
!!                     = int_cell psi*_mk_j(r) psi_nk_j+1(r) exp(-i dk.r) dr
!!
!!   with dk = b_alpha/J.  The last point, k_J = k_0 + b_alpha, uses
!!   psi(k_J) = psi(k_0) (periodic gauge), which is exact for the Bloch
!!   functions on the grid.  The Berry phase of a string is
!!   phi = -Im ln prod_j det M(k_j,k_j+1); x = phi/2pi is the sum of Wannier
!!   centres (one spin channel) in units of the cell length along alpha and
!!
!!     P_el = -(f e / Omega) xbar a_alpha,  f = 2 (no spin) or 1 per channel.
!!
!!   Only orthorhombic cells (as standard CONQUEST).  Meshes reduced by time
!!   reversal are unfolded with psi_-k = conjg(psi_k) (collinear spin only).
!!  AUTHOR
!!   CONQUEST developers
!!  CREATION DATE
!!   2026/11/11
!!  MODIFICATION HISTORY
!!  SOURCE
!!
module berry

  use datatypes

  implicit none

  private
  public :: process_berry, process_pol_difference, process_bec

  ! Strings of one direction in one structure
  type berry_dir
     integer :: nstr = 0
     real(double), allocatable, dimension(:,:) :: kperp ! (2,nstr) fractional
     real(double), allocatable, dimension(:,:) :: x     ! (nstr,nspin) phase/2pi in [-1/2,1/2)
  end type berry_dir

  ! Everything needed from one structure to form polarisation differences
  type berry_run
     character(len=256) :: label
     real(double), dimension(3) :: cell
     real(double) :: volume, spin_factor
     integer :: natoms, nspin
     integer, dimension(3) :: mesh
     integer, dimension(2) :: nocc = 0                ! 0 = not recorded
     real(double), dimension(3) :: shift = 0.0_double
     integer, allocatable, dimension(:) :: species
     real(double), allocatable, dimension(:) :: zion
     real(double), allocatable, dimension(:,:) :: pos ! (3,natoms) bohr
     type(berry_dir), dimension(3) :: dir
  end type berry_run

  ! PAO values on the grid for one atom, independent of k (built once)
  type pao_table
     integer :: npts = 0, npao = 0
     integer, allocatable, dimension(:) :: idx        ! home grid point
     integer, allocatable, dimension(:,:) :: shift    ! (3,npts) image index s: home = actual - s.L
     real(double), allocatable, dimension(:,:) :: val ! (npao,npts)
  end type pao_table
  type(pao_table), allocatable, dimension(:), save :: tables
  logical, save :: tables_built = .false.

  integer, parameter :: berry_format = 1
  real(double), parameter :: kmatch_tol = 1.0e-3_double     ! fractional k tolerance
  real(double), parameter :: string_spread_warn = 0.25_double ! in units of 2pi
  real(double), parameter :: step_warn = 0.25_double          ! in units of 2pi

!!***

contains

  ! -----------------------------------------------------------
  ! Subroutine process_berry
  ! -----------------------------------------------------------

  !!****f* berry/process_berry *
  !!
  !!  NAME
  !!   process_berry
  !!  PURPOSE
  !!   Berry-phase polarisation of the structure in the current directory;
  !!   writes the string phases to Process.BerryFile for later differences
  !!  AUTHOR
  !!   CONQUEST developers
  !!  CREATION DATE
  !!   2026/11/11
  !!  SOURCE
  !!
  subroutine process_berry

    use numbers
    use local, only: nptsx, nptsy, nptsz, grid_x, grid_y, grid_z, &
         berry_mp, berry_mp_shift, berry_direction, berry_file, berry_table_mb
    use global_module, only: nspin, ni_in_cell, atom_coord, species_glob
    use species_module, only: charge
    use dimens, only: r_super_x, r_super_y, r_super_z
    use read, only: read_eigenvalues, read_psi_coeffs
    use angular_coeff_routines, only: set_prefac_real, set_fact, set_prefac
    use GenComms, only: cq_abort, cq_warn

    implicit none

    ! Local variables
    type(berry_run) :: run
    integer :: nfull, i_spin, alpha, p1, p2, i1, i2, j, J_a, i_str, nmax, ngrid, stat, i
    integer, dimension(3) :: npts, ijk
    integer, dimension(2) :: nocc
    integer, allocatable, dimension(:) :: kfile, string_pt
    logical, allocatable, dimension(:) :: kconj
    real(double), dimension(3) :: cell, dg
    real(double), allocatable, dimension(:,:) :: fmesh
    real(double) :: gpv, sum_arg, arg, logabs, min_logabs, x
    complex(double_cplx), allocatable, dimension(:,:) :: psi_first, psi_cur, psi_nxt
    character(len=*), parameter :: sub_name = "process_berry"

    cell = (/r_super_x, r_super_y, r_super_z/)
    npts = (/nptsx, nptsy, nptsz/)
    dg = (/grid_x, grid_y, grid_z/)
    gpv = grid_x*grid_y*grid_z
    ngrid = nptsx*nptsy*nptsz
    do i=1,3
       if(abs(real(npts(i),double)*dg(i)-cell(i))>1.0e-6_double*cell(i)) &
            call cq_abort("Berry phase: real-space grid does not span the cell along axis ",i)
    end do
    ! PAO evaluation needs these tables
    call set_fact(8)
    call set_prefac(9)
    call set_prefac_real(9)
    call read_eigenvalues
    call read_psi_coeffs("Process")
    write(*,fmt='(/2x,"Berry-phase polarisation (King-Smith & Vanderbilt)")')
    write(*,fmt='(4x,"Cell (bohr):             ",3f14.8)') cell
    write(*,fmt='(4x,"Grid points:             ",3i8)') npts
    write(*,fmt='(4x,"Monkhorst-Pack mesh:     ",3i8)') berry_mp
    write(*,fmt='(4x,"Mesh shift (fractional): ",3f14.8)') berry_mp_shift
    ! Occupied bands, checks on insulating state and available coefficients
    call find_occupied_bands(nocc)
    nmax = maxval(nocc(1:nspin))
    ! Map the full mesh onto the k-points in the files (time reversal)
    call map_mesh(cell, nfull, fmesh, kfile, kconj)
    ! PAO values on the grid, reused for every k-point if they fit in memory
    call build_pao_tables(berry_table_mb)
    ! Set up the run record
    call init_run(run, cell, berry_mp, nspin)
    run%label = '.'
    run%nocc = nocc
    run%shift = berry_mp_shift
    allocate(psi_first(nmax,ngrid), psi_cur(nmax,ngrid), psi_nxt(nmax,ngrid), STAT=stat)
    if(stat/=0) call cq_abort("Berry phase: cannot allocate wavefunctions on grid ",nmax,ngrid)
    write(*,fmt='(4x,"Memory for wavefunctions on grid: ",f10.1," MB")') &
         four*real(nmax,double)*real(ngrid,double)*16.0_double/1.0e6_double
    do alpha = 1, 3
       if(berry_direction/=0 .and. berry_direction/=alpha) cycle
       p1 = 1 + mod(alpha,3)
       p2 = 1 + mod(alpha+1,3)
       J_a = berry_mp(alpha)
       if(J_a==1) call cq_warn(sub_name, &
            "One k-point along the string (Resta limit): only valid for large cells; direction ",alpha)
       run%dir(alpha)%nstr = berry_mp(p1)*berry_mp(p2)
       allocate(run%dir(alpha)%kperp(2,run%dir(alpha)%nstr), &
            run%dir(alpha)%x(run%dir(alpha)%nstr,nspin))
       allocate(string_pt(J_a))
       write(*,fmt='(/4x,"Direction ",i1,": ",i5," strings of ",i4," k-points")') alpha, &
            run%dir(alpha)%nstr, J_a
       do i_spin = 1, nspin
          i_str = 0
          do i1 = 1, berry_mp(p1)
             do i2 = 1, berry_mp(p2)
                i_str = i_str + 1
                ! Mesh points along this string, in order of increasing k_alpha
                do j = 1, J_a
                   ijk(alpha) = j
                   ijk(p1) = i1
                   ijk(p2) = i2
                   string_pt(j) = mesh_index(ijk, berry_mp)
                end do
                run%dir(alpha)%kperp(1,i_str) = fmesh(p1,string_pt(1))
                run%dir(alpha)%kperp(2,i_str) = fmesh(p2,string_pt(1))
                call build_psi(kfile(string_pt(1)), kconj(string_pt(1)), i_spin, nocc(i_spin), &
                     nmax, ngrid, psi_first)
                psi_cur = psi_first
                sum_arg = zero
                min_logabs = BIG
                do j = 1, J_a
                   if(j<J_a) then
                      call build_psi(kfile(string_pt(j+1)), kconj(string_pt(j+1)), i_spin, &
                           nocc(i_spin), nmax, ngrid, psi_nxt)
                      call overlap_phase(psi_cur, psi_nxt, nocc(i_spin), nmax, ngrid, npts, alpha, &
                           J_a, gpv, arg, logabs)
                      psi_cur = psi_nxt
                   else ! Close the string: psi(k_0 + b) = psi(k_0)
                      call overlap_phase(psi_cur, psi_first, nocc(i_spin), nmax, ngrid, npts, alpha, &
                           J_a, gpv, arg, logabs)
                   end if
                   sum_arg = sum_arg + arg
                   min_logabs = min(min_logabs, logabs)
                end do
                x = -sum_arg/twopi
                x = x - floor(x + half)
                run%dir(alpha)%x(i_str,i_spin) = x
                ! Per-band geometric mean of |det M| (1 for a dense mesh)
                min_logabs = exp(min_logabs/real(nocc(i_spin),double))
                write(*,fmt='(6x,"Spin ",i1," string ",i5," k_perp ",2f9.5," phase/2pi ",f15.11, &
                     &" min|det M|^(1/N) ",f8.5)') i_spin, i_str, run%dir(alpha)%kperp(:,i_str), x, &
                     min_logabs
                if(min_logabs < 0.7_double) call cq_warn(sub_name, &
                     "Small overlap |det M|^(1/N) on a string: mesh too coarse or not insulating ", &
                     min_logabs)
             end do
          end do
       end do
       deallocate(string_pt)
    end do
    deallocate(psi_first, psi_cur, psi_nxt)
    ! Atoms
    run%natoms = ni_in_cell
    allocate(run%species(ni_in_cell), run%zion(ni_in_cell), run%pos(3,ni_in_cell))
    do i = 1, ni_in_cell
       run%species(i) = species_glob(i)
       run%zion(i) = charge(species_glob(i))
       run%pos(:,i) = atom_coord(:,i)
    end do
    call report_polarisation(run)
    call write_berry_file(run, trim(berry_file))
    write(*,fmt='(/4x,"Berry-phase data written to ",a)') trim(berry_file)
    return
  end subroutine process_berry
  !!***

  ! -----------------------------------------------------------
  ! Subroutine find_occupied_bands
  ! -----------------------------------------------------------
  !
  ! Number of occupied bands per spin; checks that the system is an insulator
  ! with the same occupation at every k-point, and that the coefficients of
  ! all occupied bands were written out by CONQUEST.
  !
  subroutine find_occupied_bands(nocc)

    use numbers
    use local, only: nkp, efermi, eigenvalues, n_bands_total, band_active_kp, band_full_to_active, &
         berry_nocc_in, berry_net_charge
    use global_module, only: nspin, ni_in_cell, species_glob
    use species_module, only: charge
    use units, only: HaToeV
    use GenComms, only: cq_abort, cq_warn

    implicit none

    integer, dimension(2), intent(out) :: nocc

    integer :: i_spin, i_kp, i_band, n
    real(double) :: n_elec, homo, lumo
    character(len=*), parameter :: sub_name = "find_occupied_bands"

    nocc = 0
    n_elec = berry_net_charge
    do n = 1, ni_in_cell
       n_elec = n_elec + charge(species_glob(n))
    end do
    if(abs(berry_net_charge)>RD_ERR) call cq_warn(sub_name, &
         "Net charge in cell: the polarisation of a charged cell depends on the origin ", &
         berry_net_charge)
    do i_spin = 1, nspin
       ! Count bands below the Fermi level at each k-point
       do i_kp = 1, nkp
          n = count(eigenvalues(1:n_bands_total,i_kp,i_spin) < efermi(i_spin))
          if(i_kp==1) then
             nocc(i_spin) = n
          else if(n/=nocc(i_spin)) then
             call cq_abort("Berry phase: number of bands below Ef changes with k (metal?) at k-point ", &
                  i_kp, n)
          end if
       end do
       if(berry_nocc_in(i_spin)>n_bands_total) call cq_abort( &
            "Berry phase: Process.BerryNumOccupied exceeds the number of bands ", &
            berry_nocc_in(i_spin), n_bands_total)
       if(berry_nocc_in(i_spin)>0) then
          if(berry_nocc_in(i_spin)/=nocc(i_spin)) call cq_warn(sub_name, &
               "Number of occupied bands from input differs from count below Ef: ", &
               berry_nocc_in(i_spin), nocc(i_spin))
          nocc(i_spin) = berry_nocc_in(i_spin)
       end if
       if(nocc(i_spin)<1) call cq_abort("Berry phase: no occupied bands for spin ",i_spin)
       homo = maxval(eigenvalues(nocc(i_spin),1:nkp,i_spin))
       if(nocc(i_spin)<n_bands_total) then
          lumo = minval(eigenvalues(nocc(i_spin)+1,1:nkp,i_spin))
          write(*,fmt='(4x,"Spin ",i1,": ",i6," occupied bands; HOMO ",f12.6," LUMO ",f12.6, &
               &" Ha; gap ",f10.4," eV")') i_spin, nocc(i_spin), homo, lumo, (lumo-homo)*HaToeV
          if(lumo-homo < 1.0e-3_double) call cq_warn(sub_name, &
               "Band gap (eV) is (nearly) closed; the Berry phase needs an insulator ", &
               (lumo-homo)*HaToeV)
       else
          write(*,fmt='(4x,"Spin ",i1,": ",i6," occupied bands; HOMO ",f12.6," Ha")') &
               i_spin, nocc(i_spin), homo
       end if
       ! Coefficients present?
       do i_band = 1, nocc(i_spin)
          if(band_full_to_active(i_band)==0) call cq_abort( &
               "Berry phase: an occupied band is not in Process*WF.dat; set IO.maxnoWF and "// &
               "WaveFunctionsOut to bands 1..N_occ. Band ", i_band)
          do i_kp = 1, nkp
             if(band_active_kp(i_band,i_kp,i_spin)/=1) call cq_abort( &
                  "Berry phase: occupied band missing from Process*WF.dat at k-point ", i_kp, i_band)
          end do
       end do
    end do
    if(nspin==1) then
       if(abs(two*real(nocc(1),double)-n_elec)>1.0e-6_double) call cq_abort( &
            "Berry phase: 2 x occupied bands differs from the number of electrons ", &
            two*real(nocc(1),double), n_elec)
    else
       if(abs(real(nocc(1)+nocc(2),double)-n_elec)>1.0e-6_double) call cq_abort( &
            "Berry phase: occupied bands (up+down) differ from the number of electrons ", &
            real(nocc(1)+nocc(2),double), n_elec)
    end if
    return
  end subroutine find_occupied_bands

  ! -----------------------------------------------------------
  ! Function mesh_index
  ! -----------------------------------------------------------
  integer function mesh_index(ijk, mp)

    implicit none

    integer, dimension(3), intent(in) :: ijk, mp

    mesh_index = ijk(3) + (ijk(2)-1)*mp(3) + (ijk(1)-1)*mp(2)*mp(3)
  end function mesh_index

  ! -----------------------------------------------------------
  ! Subroutine map_mesh
  ! -----------------------------------------------------------
  !
  ! Rebuilds the full Monkhorst-Pack mesh exactly as CONQUEST does
  ! (initial_read_module), and finds for each mesh point the k-point in
  ! eigenvalues.dat equal to it or to minus it (meshes reduced by time
  ! reversal), modulo a reciprocal lattice vector.  The k-points read from
  ! eigenvalues.dat (5 decimals) are snapped to exact mesh values first.
  !
  subroutine map_mesh(cell, nfull, fmesh, kfile, kconj)

    use numbers
    use local, only: nkp, kx, ky, kz, berry_mp, berry_mp_shift
    use GenComms, only: cq_abort

    implicit none

    real(double), dimension(3), intent(in) :: cell
    integer, intent(out) :: nfull
    real(double), allocatable, dimension(:,:), intent(out) :: fmesh
    integer, allocatable, dimension(:), intent(out) :: kfile
    logical, allocatable, dimension(:), intent(out) :: kconj

    integer :: i, j, k, n, i_kp, n_conj
    integer, dimension(3) :: ijk
    real(double), dimension(3) :: d
    real(double), allocatable, dimension(:,:) :: kfrac
    logical :: found

    nfull = product(berry_mp)
    allocate(fmesh(3,nfull), kfile(nfull), kconj(nfull))
    do i = 1, berry_mp(1)
       do j = 1, berry_mp(2)
          do k = 1, berry_mp(3)
             ijk = (/i,j,k/)
             n = mesh_index(ijk, berry_mp)
             fmesh(:,n) = real(2*ijk - berry_mp - 1,double)/real(2*berry_mp,double) + berry_mp_shift
          end do
       end do
    end do
    ! Fractional k-points from the file, snapped to the mesh
    allocate(kfrac(3,nkp))
    do i_kp = 1, nkp
       kfrac(1,i_kp) = kx(i_kp)*cell(1)/twopi
       kfrac(2,i_kp) = ky(i_kp)*cell(2)/twopi
       kfrac(3,i_kp) = kz(i_kp)*cell(3)/twopi
       found = .false.
       do n = 1, nfull
          d = kfrac(:,i_kp) - fmesh(:,n)
          if(all(abs(d-anint(d))<kmatch_tol)) then
             kfrac(:,i_kp) = fmesh(:,n) + anint(d)
             found = .true.
             exit
          end if
       end do
       if(.not.found) call cq_abort("Berry phase: k-point in eigenvalues.dat is not on the MP mesh "// &
            "given by the Diag.MP* keywords: ", i_kp)
       kx(i_kp) = twopi*kfrac(1,i_kp)/cell(1)
       ky(i_kp) = twopi*kfrac(2,i_kp)/cell(2)
       kz(i_kp) = twopi*kfrac(3,i_kp)/cell(3)
    end do
    ! Each mesh point: a file k-point equal to it, or to minus it
    n_conj = 0
    do n = 1, nfull
       kfile(n) = 0
       kconj(n) = .false.
       do i_kp = 1, nkp
          d = kfrac(:,i_kp) - fmesh(:,n)
          if(all(abs(d-anint(d))<kmatch_tol)) then
             kfile(n) = i_kp
             exit
          end if
       end do
       if(kfile(n)==0) then
          do i_kp = 1, nkp
             d = -kfrac(:,i_kp) - fmesh(:,n)
             if(all(abs(d-anint(d))<kmatch_tol)) then
                kfile(n) = i_kp
                kconj(n) = .true.
                n_conj = n_conj + 1
                exit
             end if
          end do
       end if
       if(kfile(n)==0) call cq_abort("Berry phase: mesh point not found in eigenvalues.dat "// &
            "(neither k nor -k): ", n)
    end do
    write(*,fmt='(4x,"Full mesh: ",i6," k-points; ",i6," in files, ",i6," from time reversal")') &
         nfull, nkp, n_conj
    deallocate(kfrac)
    return
  end subroutine map_mesh

  ! -----------------------------------------------------------
  ! Subroutine build_psi
  ! -----------------------------------------------------------
  !
  ! Occupied Bloch functions at file k-point i_kp on the real-space grid,
  ! psi(band, grid point), with grid point (ix,iy,iz) at ((ix-1)dx, ...).
  ! Normalised so that sum_r |psi|^2 dV = 1 over the cell.  With conj the
  ! complex conjugate (the Bloch function at -k) is returned.
  !
  subroutine build_psi(i_kp, conj, i_spin, nocc, nmax, ngrid, psi)

    use numbers
    use local, only: nptsx, nptsy, nptsz, grid_x, grid_y, grid_z, evec_coeff, kx, ky, kz, &
         band_full_to_active
    use global_module, only: ni_in_cell, atom_coord, species_glob
    use pao_format, only: pao
    use dimens, only: RadiusAtomf, r_super_x, r_super_y, r_super_z
    use species_module, only: nsf_species
    use angular_coeff_routines, only: evaluate_pao
    use GenComms, only: cq_abort

    implicit none

    integer, intent(in) :: i_kp, i_spin, nocc, nmax, ngrid
    logical, intent(in) :: conj
    complex(double_cplx), dimension(nmax,ngrid), intent(out) :: psi

    integer :: i_atom, i_spec, i_l, i_zeta, i_m, npao, np, i_band, ib
    integer :: ix, iy, iz, jx, jy, jz, sx, sy, sz, minx, maxx, miny, maxy, minz, maxz, idx
    real(double) :: dx, dy, dz, rc2, phase_atom, ph
    real(double), dimension(3) :: dg, cell, kvec
    real(double), allocatable, dimension(:) :: vals
    real(double), allocatable, dimension(:,:) :: cr, ci, wr, wi
    complex(double_cplx), allocatable, dimension(:,:) :: coefT
    complex(double_cplx) :: phase
    integer :: p0, nc
    integer, parameter :: chunk = 2048

    psi = cmplx(zero,zero,double_cplx)
    dg = (/grid_x, grid_y, grid_z/)
    cell = (/r_super_x, r_super_y, r_super_z/)
    kvec = (/kx(i_kp), ky(i_kp), kz(i_kp)/)
    allocate(vals(size(evec_coeff,1)), coefT(nocc,size(evec_coeff,1)))
    if(tables_built) then
       ! Fast path: PAO values stored; only phases and coefficients change with k.
       ! W = C^T val for a chunk of points (two dgemm for real and imaginary
       ! parts of C), then psi(:,idx) += phase * W(:,p)
       allocate(cr(nocc,size(evec_coeff,1)), ci(nocc,size(evec_coeff,1)), &
            wr(nocc,chunk), wi(nocc,chunk))
       do i_atom = 1, ni_in_cell
          npao = tables(i_atom)%npao
          do ib = 1, nocc
             i_band = band_full_to_active(ib)
             cr(ib,1:npao) = real(evec_coeff(1:npao, i_atom, i_band, i_kp, i_spin),double)
             ci(ib,1:npao) = aimag(evec_coeff(1:npao, i_atom, i_band, i_kp, i_spin))
          end do
          phase_atom = dot_product(kvec, atom_coord(:,i_atom))
          do p0 = 1, tables(i_atom)%npts, chunk
             nc = min(chunk, tables(i_atom)%npts - p0 + 1)
             call dgemm('N','N', nocc, nc, npao, one, cr, nocc, tables(i_atom)%val(1,p0), &
                  npao, zero, wr, nocc)
             call dgemm('N','N', nocc, nc, npao, one, ci, nocc, tables(i_atom)%val(1,p0), &
                  npao, zero, wi, nocc)
             do np = p0, p0 + nc - 1
                ph = phase_atom - kvec(1)*cell(1)*real(tables(i_atom)%shift(1,np),double) &
                     - kvec(2)*cell(2)*real(tables(i_atom)%shift(2,np),double) &
                     - kvec(3)*cell(3)*real(tables(i_atom)%shift(3,np),double)
                phase = cmplx(cos(ph),sin(ph),double_cplx)
                idx = tables(i_atom)%idx(np)
                psi(1:nocc,idx) = psi(1:nocc,idx) + &
                     phase*cmplx(wr(1:nocc,np-p0+1), wi(1:nocc,np-p0+1), double_cplx)
             end do
          end do
       end do
       if(conj) psi(1:nocc,:) = conjg(psi(1:nocc,:))
       deallocate(vals, coefT, cr, ci, wr, wi)
       return
    end if
    do i_atom = 1, ni_in_cell
       i_spec = species_glob(i_atom)
       ! Number of PAOs on this atom
       npao = 0
       do i_l = 0, pao(i_spec)%greatest_angmom
          npao = npao + (2*i_l+1)*pao(i_spec)%angmom(i_l)%n_zeta_in_angmom
       end do
       if(npao>size(evec_coeff,1) .or. npao/=nsf_species(i_spec)) call cq_abort("Berry phase: PAO count differs from coefficients read "// &
            "(multi-site support functions are not supported) on atom ", i_atom, npao)
       do ib = 1, nocc
          i_band = band_full_to_active(ib)
          coefT(ib,1:npao) = evec_coeff(1:npao, i_atom, i_band, i_kp, i_spin)
       end do
       phase_atom = dot_product(kvec, atom_coord(:,i_atom))
       rc2 = RadiusAtomf(i_spec)**2
       minx = floor((atom_coord(1,i_atom) - RadiusAtomf(i_spec))/dg(1))
       maxx = floor((atom_coord(1,i_atom) + RadiusAtomf(i_spec))/dg(1)) + 1
       miny = floor((atom_coord(2,i_atom) - RadiusAtomf(i_spec))/dg(2))
       maxy = floor((atom_coord(2,i_atom) + RadiusAtomf(i_spec))/dg(2)) + 1
       minz = floor((atom_coord(3,i_atom) - RadiusAtomf(i_spec))/dg(3))
       maxz = floor((atom_coord(3,i_atom) + RadiusAtomf(i_spec))/dg(3)) + 1
       do iz = minz, maxz
          dz = dg(3)*real(iz,double) - atom_coord(3,i_atom)
          jz = modulo(iz,nptsz) + 1
          sz = (iz - modulo(iz,nptsz))/nptsz   ! image index: home point = actual - sz*L
          do iy = miny, maxy
             dy = dg(2)*real(iy,double) - atom_coord(2,i_atom)
             jy = modulo(iy,nptsy) + 1
             sy = (iy - modulo(iy,nptsy))/nptsy
             do ix = minx, maxx
                dx = dg(1)*real(ix,double) - atom_coord(1,i_atom)
                if(dx*dx+dy*dy+dz*dz > rc2) cycle
                jx = modulo(ix,nptsx) + 1
                sx = (ix - modulo(ix,nptsx))/nptsx
                ! Contribution of the image atom at tau - s.L to the home grid point
                ph = phase_atom - kvec(1)*cell(1)*real(sx,double) - kvec(2)*cell(2)*real(sy,double) &
                     - kvec(3)*cell(3)*real(sz,double)
                phase = cmplx(cos(ph),sin(ph),double_cplx)
                np = 0
                do i_l = 0, pao(i_spec)%greatest_angmom
                   do i_zeta = 1, pao(i_spec)%angmom(i_l)%n_zeta_in_angmom
                      do i_m = -i_l, i_l
                         np = np + 1
                         call evaluate_pao(i_spec,i_l,i_zeta,i_m,dx,dy,dz,vals(np))
                      end do
                   end do
                end do
                idx = jx + (jy-1)*nptsx + (jz-1)*nptsx*nptsy
                psi(1:nocc,idx) = psi(1:nocc,idx) + phase*matmul(coefT(1:nocc,1:npao), vals(1:npao))
             end do
          end do
       end do
    end do
    if(conj) psi(1:nocc,:) = conjg(psi(1:nocc,:))
    deallocate(vals, coefT)
    return
  end subroutine build_psi

  ! -----------------------------------------------------------
  ! Subroutine build_pao_tables
  ! -----------------------------------------------------------
  !
  ! Stores the PAO values of every atom on the grid points within its
  ! radius, with the home grid point and lattice image of each point, if
  ! the tables fit into max_mb megabytes.  build_psi then only applies the
  ! Bloch phases and coefficients for each k-point.
  !
  subroutine build_pao_tables(max_mb)

    use numbers
    use local, only: nptsx, nptsy, nptsz, grid_x, grid_y, grid_z, evec_coeff
    use global_module, only: ni_in_cell, atom_coord, species_glob
    use pao_format, only: pao
    use dimens, only: RadiusAtomf
    use species_module, only: nsf_species
    use angular_coeff_routines, only: evaluate_pao
    use GenComms, only: cq_abort

    implicit none

    real(double), intent(in) :: max_mb

    integer :: i_atom, i_spec, i_l, i_zeta, i_m, npao, np, n, pass, stat
    integer :: ix, iy, iz, minx, maxx, miny, maxy, minz, maxz
    real(double) :: dx, dy, dz, rc2, mbytes
    real(double), dimension(3) :: dg

    dg = (/grid_x, grid_y, grid_z/)
    allocate(tables(ni_in_cell))
    mbytes = zero
    do pass = 1, 2 ! 1: count points, 2: fill
       do i_atom = 1, ni_in_cell
          i_spec = species_glob(i_atom)
          npao = 0
          do i_l = 0, pao(i_spec)%greatest_angmom
             npao = npao + (2*i_l+1)*pao(i_spec)%angmom(i_l)%n_zeta_in_angmom
          end do
          if(npao>size(evec_coeff,1) .or. npao/=nsf_species(i_spec)) call cq_abort("Berry phase: PAO count differs from coefficients read "// &
               "(multi-site support functions are not supported) on atom ", i_atom, npao)
          if(pass==2) then
             n = tables(i_atom)%npts
             allocate(tables(i_atom)%idx(n), tables(i_atom)%shift(3,n), tables(i_atom)%val(npao,n), &
                  STAT=stat)
             if(stat/=0) call cq_abort("Berry phase: cannot allocate PAO table for atom ", i_atom)
          end if
          tables(i_atom)%npao = npao
          rc2 = RadiusAtomf(i_spec)**2
          minx = floor((atom_coord(1,i_atom) - RadiusAtomf(i_spec))/dg(1))
          maxx = floor((atom_coord(1,i_atom) + RadiusAtomf(i_spec))/dg(1)) + 1
          miny = floor((atom_coord(2,i_atom) - RadiusAtomf(i_spec))/dg(2))
          maxy = floor((atom_coord(2,i_atom) + RadiusAtomf(i_spec))/dg(2)) + 1
          minz = floor((atom_coord(3,i_atom) - RadiusAtomf(i_spec))/dg(3))
          maxz = floor((atom_coord(3,i_atom) + RadiusAtomf(i_spec))/dg(3)) + 1
          n = 0
          do iz = minz, maxz
             dz = dg(3)*real(iz,double) - atom_coord(3,i_atom)
             do iy = miny, maxy
                dy = dg(2)*real(iy,double) - atom_coord(2,i_atom)
                do ix = minx, maxx
                   dx = dg(1)*real(ix,double) - atom_coord(1,i_atom)
                   if(dx*dx+dy*dy+dz*dz > rc2) cycle
                   n = n + 1
                   if(pass==2) then
                      tables(i_atom)%idx(n) = modulo(ix,nptsx) + 1 + modulo(iy,nptsy)*nptsx + &
                           modulo(iz,nptsz)*nptsx*nptsy
                      tables(i_atom)%shift(1,n) = (ix - modulo(ix,nptsx))/nptsx
                      tables(i_atom)%shift(2,n) = (iy - modulo(iy,nptsy))/nptsy
                      tables(i_atom)%shift(3,n) = (iz - modulo(iz,nptsz))/nptsz
                      np = 0
                      do i_l = 0, pao(i_spec)%greatest_angmom
                         do i_zeta = 1, pao(i_spec)%angmom(i_l)%n_zeta_in_angmom
                            do i_m = -i_l, i_l
                               np = np + 1
                               call evaluate_pao(i_spec,i_l,i_zeta,i_m,dx,dy,dz,tables(i_atom)%val(np,n))
                            end do
                         end do
                      end do
                   end if
                end do
             end do
          end do
          if(pass==1) then
             tables(i_atom)%npts = n
             mbytes = mbytes + real(n,double)*(16.0_double + 8.0_double*real(npao,double))/1.0e6_double
          end if
       end do
       if(pass==1) then
          if(mbytes>max_mb) then
             write(*,fmt='(4x,"PAO tables would need ",f10.1," MB > Process.BerryTableMB = ",f10.1, &
                  &"; evaluating PAOs for each k-point")') mbytes, max_mb
             deallocate(tables)
             return
          end if
          write(*,fmt='(4x,"PAO tables on grid: ",f10.1," MB")') mbytes
       end if
    end do
    tables_built = .true.
    return
  end subroutine build_pao_tables

  ! -----------------------------------------------------------
  ! Subroutine overlap_phase
  ! -----------------------------------------------------------
  !
  ! M_mn = sum_r conjg(psiA_m(r)) psiB_n(r) exp(-i dk.r) dV, dk = b_alpha/J;
  ! returns arg det M and ln|det M| from the LU decomposition (no overflow).
  !
  subroutine overlap_phase(psiA, psiB, n, nmax, ngrid, npts, alpha, J, gpv, arg, logabs)

    use numbers
    use GenComms, only: cq_abort

    implicit none

    integer, intent(in) :: n, nmax, ngrid, alpha, J
    integer, dimension(3), intent(in) :: npts
    complex(double_cplx), dimension(nmax,ngrid), intent(in) :: psiA, psiB
    real(double), intent(in) :: gpv
    real(double), intent(out) :: arg, logabs

    integer :: ix, iy, iz, idx, ia, i, info
    integer, dimension(3) :: ijk
    integer, allocatable, dimension(:) :: ipiv
    real(double) :: t
    complex(double_cplx), allocatable, dimension(:) :: ph
    complex(double_cplx), allocatable, dimension(:,:) :: Bp, MT

    allocate(ph(npts(alpha)), Bp(n,ngrid), MT(n,n), ipiv(n))
    do ia = 1, npts(alpha)
       t = -twopi*real(ia-1,double)/(real(J,double)*real(npts(alpha),double))
       ph(ia) = cmplx(cos(t),sin(t),double_cplx)
    end do
    do iz = 1, npts(3)
       ijk(3) = iz
       do iy = 1, npts(2)
          ijk(2) = iy
          do ix = 1, npts(1)
             ijk(1) = ix
             idx = ix + (iy-1)*npts(1) + (iz-1)*npts(1)*npts(2)
             Bp(1:n,idx) = psiB(1:n,idx)*ph(ijk(alpha))
          end do
       end do
    end do
    ! MT(i,j) = sum_r Bp(i,r) conjg(psiA(j,r)) = M(j,i)
    call zgemm('N','C', n, n, ngrid, cmplx(gpv,zero,double_cplx), Bp, n, psiA, nmax, &
         cmplx(zero,zero,double_cplx), MT, n)
    call zgetrf(n, n, MT, n, ipiv, info)
    if(info/=0) call cq_abort("Berry phase: singular overlap matrix between neighbouring k-points ",info)
    arg = zero
    logabs = zero
    do i = 1, n
       arg = arg + atan2(aimag(MT(i,i)), real(MT(i,i),double))
       logabs = logabs + log(abs(MT(i,i)))
       if(ipiv(i)/=i) arg = arg + pi
    end do
    deallocate(ph, Bp, MT, ipiv)
    return
  end subroutine overlap_phase

  ! -----------------------------------------------------------
  ! Subroutine init_run
  ! -----------------------------------------------------------
  subroutine init_run(run, cell, mesh, nspin)

    use numbers

    implicit none

    type(berry_run), intent(inout) :: run
    real(double), dimension(3), intent(in) :: cell
    integer, dimension(3), intent(in) :: mesh
    integer, intent(in) :: nspin

    run%cell = cell
    run%volume = cell(1)*cell(2)*cell(3)
    run%mesh = mesh
    run%nspin = nspin
    if(nspin==1) then
       run%spin_factor = two
    else
       run%spin_factor = one
    end if
    run%dir(:)%nstr = 0
    return
  end subroutine init_run

  ! -----------------------------------------------------------
  ! Subroutine average_strings
  ! -----------------------------------------------------------
  !
  ! Average of string phases (units of 2pi) defined modulo 1: each phase is
  ! brought to the branch nearest the running mean.  Returns the spread.
  !
  subroutine average_strings(x, xbar, spread)

    use numbers

    implicit none

    real(double), dimension(:), intent(in) :: x
    real(double), intent(out) :: xbar, spread

    integer :: i, iter, n
    real(double), allocatable, dimension(:) :: y

    n = size(x)
    allocate(y(n))
    xbar = x(1)
    do iter = 1, 3
       do i = 1, n
          y(i) = x(i) - anint(x(i) - xbar)
       end do
       xbar = sum(y)/real(n,double)
    end do
    spread = maxval(abs(y - xbar))
    deallocate(y)
    return
  end subroutine average_strings

  ! -----------------------------------------------------------
  ! Subroutine report_polarisation
  ! -----------------------------------------------------------
  subroutine report_polarisation(run)

    use numbers
    use units, only: BohrToAng, eVToJ
    use GenComms, only: cq_warn

    implicit none

    type(berry_run), intent(in) :: run

    integer :: alpha, i_spin
    real(double) :: xbar, spread, fac_C, pel, pion, ptot, pq, pred
    character(len=*), parameter :: sub_name = "report_polarisation"

    fac_C = eVToJ/(BohrToAng*1.0e-10_double)**2  ! e/bohr^2 -> C/m^2
    write(*,fmt='(/4x,"Polarisation (electronic, ionic, total)")')
    write(*,fmt='(4x,"Cell volume ",f16.6," bohr^3; spin factor ",f4.1)') run%volume, run%spin_factor
    do alpha = 1, 3
       if(run%dir(alpha)%nstr==0) cycle
       pel = zero
       do i_spin = 1, run%nspin
          call average_strings(run%dir(alpha)%x(:,i_spin), xbar, spread)
          write(*,fmt='(/4x,"Direction ",i1," spin ",i1,": mean phase/2pi ",f15.11, &
               &"  spread over strings ",f12.8)') alpha, i_spin, xbar, spread
          if(spread>string_spread_warn) call cq_warn(sub_name, &
               "Berry phases of strings disagree; increase the k-point mesh. Spread ", spread)
          pel = pel - run%spin_factor*xbar*run%cell(alpha)/run%volume
       end do
       pion = sum(run%zion(:)*run%pos(alpha,:))/run%volume
       ptot = pel + pion
       pq = run%cell(alpha)/run%volume
       pred = ptot - pq*anint(ptot/pq)
       write(*,fmt='(4x,"Direction ",i1)') alpha
       write(*,fmt='(6x,"P electronic         ",es20.11," e/bohr^2")') pel
       write(*,fmt='(6x,"P ionic              ",es20.11," e/bohr^2")') pion
       write(*,fmt='(6x,"P total              ",es20.11," e/bohr^2",f14.6," C/m^2",f14.6," uC/cm^2")') &
            ptot, ptot*fac_C, ptot*fac_C*100.0_double
       write(*,fmt='(6x,"Quantum e.a/Omega    ",es20.11," e/bohr^2",f14.6," C/m^2",f14.6," uC/cm^2")') &
            pq, pq*fac_C, pq*fac_C*100.0_double
       write(*,fmt='(6x,"P total mod quantum  ",es20.11," e/bohr^2",f14.6," C/m^2",f14.6," uC/cm^2")') &
            pred, pred*fac_C, pred*fac_C*100.0_double
    end do
    write(*,fmt='(/4x,"Only polarisation differences between structures with the same cell are physical;")')
    write(*,fmt='(4x,"use Process.Job dpo (mode effective charge) or bec (Born effective charges).")')
    return
  end subroutine report_polarisation

  ! -----------------------------------------------------------
  ! Subroutine write_berry_file
  ! -----------------------------------------------------------
  subroutine write_berry_file(run, filename)

    use input_module, only: io_assign, io_close

    implicit none

    type(berry_run), intent(in) :: run
    character(len=*), intent(in) :: filename

    integer :: lun, i, alpha

    call io_assign(lun)
    open(unit=lun, file=filename, status='replace')
    write(lun,'(a)') '# CONQUEST PostProcessCQ Berry-phase polarisation data (atomic units, bohr)'
    write(lun,'(a)') '# Atoms: index species Z_ion x y z; Direction: alpha nstrings;'
    write(lun,'(a)') '# string lines: k_perp(2, fractional) phase/2pi per spin channel in [-1/2,1/2)'
    write(lun,'("BerryFormat ",i4)') berry_format
    write(lun,'("Cell ",3es25.16)') run%cell
    write(lun,'("NSpin ",i4)') run%nspin
    write(lun,'("SpinFactor ",f6.2)') run%spin_factor
    write(lun,'("Mesh ",3i6)') run%mesh
    write(lun,'("Shift ",3es25.16)') run%shift
    write(lun,'("NOcc ",2i8)') run%nocc(1:run%nspin)
    write(lun,'("NAtoms ",i8)') run%natoms
    write(lun,'(a)') 'Atoms'
    do i = 1, run%natoms
       write(lun,'(2i8,f14.8,3es25.16)') i, run%species(i), run%zion(i), run%pos(:,i)
    end do
    do alpha = 1, 3
       if(run%dir(alpha)%nstr==0) cycle
       write(lun,'("Direction ",2i8)') alpha, run%dir(alpha)%nstr
       do i = 1, run%dir(alpha)%nstr
          write(lun,'(2f16.11,2es25.16)') run%dir(alpha)%kperp(:,i), run%dir(alpha)%x(i,1:run%nspin)
       end do
    end do
    write(lun,'(a)') 'End'
    call io_close(lun)
    return
  end subroutine write_berry_file

  ! -----------------------------------------------------------
  ! Subroutine read_berry_file
  ! -----------------------------------------------------------
  subroutine read_berry_file(run, filename)

    use numbers
    use input_module, only: io_assign, io_close
    use GenComms, only: cq_abort

    implicit none

    type(berry_run), intent(inout) :: run
    character(len=*), intent(in) :: filename

    integer :: lun, i, idum, alpha, nstr, ios, fmt_in
    character(len=512) :: line
    character(len=32) :: key
    logical :: exists

    inquire(file=filename, exist=exists)
    if(.not.exists) call cq_abort("Berry phase: data file not found: "//trim(filename))
    call io_assign(lun)
    open(unit=lun, file=filename, status='old')
    run%natoms = 0
    run%nspin = 0
    run%dir(:)%nstr = 0
    fmt_in = 0
    do
       read(lun,'(a)',iostat=ios) line
       if(ios/=0) call cq_abort("Berry phase: unexpected end of data file "//trim(filename))
       line = adjustl(line)
       if(len_trim(line)==0) cycle
       if(line(1:1)=='#') cycle
       read(line,*) key
       select case(trim(key))
       case('BerryFormat')
          read(line,*) key, fmt_in
          if(fmt_in/=berry_format) call cq_abort("Berry phase: unknown data file format ",fmt_in)
       case('Cell')
          read(line,*) key, run%cell
          run%volume = run%cell(1)*run%cell(2)*run%cell(3)
       case('NSpin')
          read(line,*) key, run%nspin
       case('SpinFactor')
          read(line,*) key, run%spin_factor
       case('Mesh')
          read(line,*) key, run%mesh
       case('Shift')
          read(line,*) key, run%shift
       case('NOcc')
          if(run%nspin==0) call cq_abort("Berry phase: NOcc before NSpin in "//trim(filename))
          read(line,*) key, run%nocc(1:run%nspin)
       case('NAtoms')
          read(line,*) key, run%natoms
          allocate(run%species(run%natoms), run%zion(run%natoms), run%pos(3,run%natoms))
       case('Atoms')
          if(run%natoms==0) call cq_abort("Berry phase: Atoms before NAtoms in "//trim(filename))
          do i = 1, run%natoms
             read(lun,*) idum, run%species(i), run%zion(i), run%pos(:,i)
          end do
       case('Direction')
          if(run%nspin==0) call cq_abort("Berry phase: Direction before NSpin in "//trim(filename))
          read(line,*) key, alpha, nstr
          run%dir(alpha)%nstr = nstr
          allocate(run%dir(alpha)%kperp(2,nstr), run%dir(alpha)%x(nstr,run%nspin))
          do i = 1, nstr
             read(lun,*) run%dir(alpha)%kperp(:,i), run%dir(alpha)%x(i,1:run%nspin)
          end do
       case('End')
          exit
       case default
          call cq_abort("Berry phase: unknown keyword in data file "//trim(filename)//": "//trim(key))
       end select
    end do
    call io_close(lun)
    if(fmt_in==0 .or. run%natoms==0) call cq_abort("Berry phase: incomplete data file "//trim(filename))
    return
  end subroutine read_berry_file

  ! -----------------------------------------------------------
  ! Subroutine load_runs
  ! -----------------------------------------------------------
  subroutine load_runs(runs)

    use local, only: berry_runs, berry_n_runs, berry_file
    use GenComms, only: cq_abort

    implicit none

    type(berry_run), allocatable, dimension(:), intent(out) :: runs

    integer :: i

    if(berry_n_runs<2) call cq_abort("Berry phase: need at least two runs in Process.PolarisationRuns")
    allocate(runs(berry_n_runs))
    do i = 1, berry_n_runs
       runs(i)%label = berry_runs(i)
       call read_berry_file(runs(i), trim(berry_runs(i))//'/'//trim(berry_file))
       if(i>1) call check_compatible(runs(1), runs(i))
    end do
    return
  end subroutine load_runs

  ! -----------------------------------------------------------
  ! Subroutine check_compatible
  ! -----------------------------------------------------------
  subroutine check_compatible(a, b)

    use GenComms, only: cq_abort

    implicit none

    type(berry_run), intent(in) :: a, b

    integer :: alpha

    if(any(abs(a%cell-b%cell)>1.0e-8_double*maxval(a%cell))) &
         call cq_abort("Berry phase: different cells in "//trim(a%label)//" and "//trim(b%label))
    if(a%natoms/=b%natoms) call cq_abort("Berry phase: different numbers of atoms in "// &
         trim(a%label)//" and "//trim(b%label))
    if(any(a%species/=b%species)) call cq_abort("Berry phase: different species order in "// &
         trim(a%label)//" and "//trim(b%label))
    if(a%nspin/=b%nspin) call cq_abort("Berry phase: different spin treatment in "// &
         trim(a%label)//" and "//trim(b%label))
    if(any(a%mesh/=b%mesh)) call cq_abort("Berry phase: different k-point meshes in "// &
         trim(a%label)//" and "//trim(b%label))
    if(all(a%nocc(1:a%nspin)>0) .and. all(b%nocc(1:a%nspin)>0) .and. &
         any(a%nocc(1:a%nspin)/=b%nocc(1:a%nspin))) call cq_abort( &
         "Berry phase: different numbers of occupied bands in "//trim(a%label)//" and "//trim(b%label))
    do alpha = 1, 3
       if(a%dir(alpha)%nstr==0 .or. b%dir(alpha)%nstr==0) cycle
       if(a%dir(alpha)%nstr/=b%dir(alpha)%nstr) call cq_abort("Berry phase: different strings in "// &
            trim(a%label)//" and "//trim(b%label), alpha)
       if(any(abs(a%dir(alpha)%kperp-b%dir(alpha)%kperp)>1.0e-6_double)) call cq_abort( &
            "Berry phase: different k-point strings (mesh shift?) in "//trim(a%label)//" and "// &
            trim(b%label), alpha)
    end do
    return
  end subroutine check_compatible

  ! -----------------------------------------------------------
  ! Subroutine delta_pol
  ! -----------------------------------------------------------
  !
  ! Polarisation change from run a to run b (same cell and mesh).  Each
  ! string's phase change is taken on the branch nearest zero, so the result
  ! is exact when every |dphase/2pi| < 1/2 (small displacements); the ionic
  ! part uses minimum-image displacements, so atoms wrapped across the cell
  ! boundary do not add a quantum.
  !
  subroutine delta_pol(a, b, dP_el, dP_ion, du, have, max_dx, max_spread)

    use numbers

    implicit none

    type(berry_run), intent(in) :: a, b
    real(double), dimension(3), intent(out) :: dP_el, dP_ion
    real(double), dimension(:,:), intent(out) :: du
    logical, dimension(3), intent(out) :: have
    real(double), intent(out) :: max_dx, max_spread

    integer :: alpha, i_spin, i, n
    real(double) :: dx, mean, spread
    real(double), allocatable, dimension(:) :: d

    do i = 1, a%natoms
       du(:,i) = b%pos(:,i) - a%pos(:,i)
       du(:,i) = du(:,i) - a%cell(:)*anint(du(:,i)/a%cell(:))
    end do
    do alpha = 1, 3
       dP_ion(alpha) = sum(a%zion(:)*du(alpha,:))/a%volume
    end do
    dP_el = zero
    max_dx = zero
    max_spread = zero
    do alpha = 1, 3
       have(alpha) = a%dir(alpha)%nstr>0 .and. b%dir(alpha)%nstr==a%dir(alpha)%nstr
       if(.not.have(alpha)) cycle
       n = a%dir(alpha)%nstr
       allocate(d(n))
       do i_spin = 1, a%nspin
          do i = 1, n
             dx = b%dir(alpha)%x(i,i_spin) - a%dir(alpha)%x(i,i_spin)
             d(i) = dx - anint(dx)
          end do
          mean = sum(d)/real(n,double)
          spread = maxval(abs(d - mean))
          max_dx = max(max_dx, maxval(abs(d)))
          max_spread = max(max_spread, spread)
          dP_el(alpha) = dP_el(alpha) - a%spin_factor*mean*a%cell(alpha)/a%volume
       end do
       deallocate(d)
    end do
    return
  end subroutine delta_pol

  ! -----------------------------------------------------------
  ! Subroutine process_pol_difference
  ! -----------------------------------------------------------

  !!****f* berry/process_pol_difference *
  !!
  !!  NAME
  !!   process_pol_difference
  !!  PURPOSE
  !!   Polarisation change along the sequence of structures listed in
  !!   Process.PolarisationRuns (first = reference), accumulated step by step
  !!   so that the branch is followed, and the mode effective charge
  !!     Z*_mode,alpha = (Omega/e) dP_alpha / |du|,  |du| = sqrt(sum_k |du_k|^2)
  !!   of the total distortion du.
  !!  AUTHOR
  !!   CONQUEST developers
  !!  CREATION DATE
  !!   2026/11/11
  !!  SOURCE
  !!
  subroutine process_pol_difference

    use numbers
    use units, only: BohrToAng, eVToJ
    use species_module, only: species_label
    use GenComms, only: cq_abort, cq_warn

    implicit none

    type(berry_run), allocatable, dimension(:) :: runs
    integer :: i, n, alpha, natoms
    logical, dimension(3) :: have, have_all
    real(double), dimension(3) :: dP_el, dP_ion, P_el, P_ion, P_tot, zmode
    real(double), allocatable, dimension(:,:) :: du, du_tot
    real(double) :: max_dx, max_spread, fac_C, norm_u, worst
    character(len=*), parameter :: sub_name = "process_pol_difference"

    fac_C = eVToJ/(BohrToAng*1.0e-10_double)**2
    call load_runs(runs)
    n = size(runs)
    natoms = runs(1)%natoms
    allocate(du(3,natoms), du_tot(3,natoms))
    write(*,fmt='(/2x,"Polarisation change along ",i4," structures (reference: ",a,")")') n, &
         trim(runs(1)%label)
    P_el = zero
    P_ion = zero
    du_tot = zero
    have_all = .true.
    worst = zero
    write(*,fmt='(/4x,"Step  |du| (bohr)   dP_x            dP_y            dP_z  (e/bohr^2)  max|dphase/2pi|")')
    do i = 2, n
       call delta_pol(runs(i-1), runs(i), dP_el, dP_ion, du, have, max_dx, max_spread)
       have_all = have_all .and. have
       P_el = P_el + dP_el
       P_ion = P_ion + dP_ion
       du_tot = du_tot + du
       worst = max(worst, max_dx)
       write(*,fmt='(4x,i4,f12.6,3es16.7,f12.6,2x,a)') i-1, sqrt(sum(du*du)), dP_el+dP_ion, max_dx, &
            trim(runs(i)%label)
       if(max_dx>step_warn) call cq_warn(sub_name, "Large Berry-phase change in one step; the "// &
            "branch may be wrong. Add intermediate structures. Step, max|dphase/2pi| ", &
            real(i-1,double), max_dx)
       if(max_spread>string_spread_warn) call cq_warn(sub_name, &
            "Phase changes of strings disagree; increase the k-point mesh. Step, spread ", &
            real(i-1,double), max_spread)
    end do
    P_tot = P_el + P_ion
    norm_u = sqrt(sum(du_tot*du_tot))
    write(*,fmt='(/4x,"Total change (reference -> ",a,")")') trim(runs(n)%label)
    do alpha = 1, 3
       if(.not.have_all(alpha)) then
          write(*,fmt='(6x,"Direction ",i1,": no Berry phase data")') alpha
          cycle
       end if
       write(*,fmt='(6x,"Direction ",i1,": dP_el ",es16.7," dP_ion ",es16.7," dP ",es16.7, &
            &" e/bohr^2 = ",f12.6," uC/cm^2")') alpha, P_el(alpha), P_ion(alpha), P_tot(alpha), &
            P_tot(alpha)*fac_C*100.0_double
    end do
    write(*,fmt='(6x,"|du| = sqrt(sum_k |du_k|^2) = ",f14.8," bohr = ",f14.8," A")') norm_u, &
         norm_u*BohrToAng
    if(norm_u<1.0e-8_double) call cq_abort("Berry phase: the structures are identical (du = 0)")
    zmode = zero
    do alpha = 1, 3
       if(have_all(alpha)) zmode(alpha) = runs(1)%volume*P_tot(alpha)/norm_u
    end do
    write(*,fmt='(/4x,"Mode effective charge Z*_mode = (Omega/e) dP/|du| (e): ",3f14.6)') zmode
    write(*,fmt='(4x,"Norm of Z*_mode (e): ",f14.6)') sqrt(sum(zmode*zmode))
    write(*,fmt='(/4x,"Unit displacement pattern du_k/|du|:")')
    do i = 1, natoms
       write(*,fmt='(6x,i6,2x,a4,3f12.7)') i, species_label(runs(1)%species(i)), du_tot(:,i)/norm_u
    end do
    if(n==2 .and. worst>0.1_double) write(*,fmt='(/4x,"Note: one step with max |dphase/2pi| = ",f8.4, &
         &"; check the branch with intermediate structures")') worst
    write(*,fmt='(/4x,"Note: one collective distortion gives three numbers (dP_x, dP_y, dP_z); it cannot")')
    write(*,fmt='(4x,"determine the 3N x 3 atomic Born effective charges, which need 3N independent")')
    write(*,fmt='(4x,"displacements (Process.Job bec).")')
    deallocate(du, du_tot, runs)
    return
  end subroutine process_pol_difference
  !!***

  ! -----------------------------------------------------------
  ! Subroutine process_bec
  ! -----------------------------------------------------------

  !!****f* berry/process_bec *
  !!
  !!  NAME
  !!   process_bec
  !!  PURPOSE
  !!   Born effective charges Z*_k,ab = (Omega/e) dP_a/du_k,b from runs in
  !!   which one Cartesian coordinate of one atom is displaced from the
  !!   reference (first entry of Process.PolarisationRuns).  The displaced
  !!   atom and direction are found from the coordinates.  For each (k,b) the
  !!   slope is the least-squares fit through the origin of dP against the
  !!   displacement, sum(d dP)/sum(d^2): (dP(+d)-dP(-d))/2d for a +/- pair of
  !!   equal size (central difference), dP/d for a single run (one-sided).  The ionic charge is included
  !!   through dP_ion.  Runs that move more than one coordinate are rejected.
  !!  AUTHOR
  !!   CONQUEST developers
  !!  CREATION DATE
  !!   2026/11/11
  !!  SOURCE
  !!
  subroutine process_bec

    use numbers
    use local, only: bec_disp_tol, flag_bec_asr
    use species_module, only: species_label
    use GenComms, only: cq_abort, cq_warn

    implicit none

    type(berry_run), allocatable, dimension(:) :: runs
    integer :: i, n, natoms, k, a, b, nmoved, kk, bb, n_skip, n_used
    logical, dimension(3) :: have
    logical :: complete
    logical, allocatable, dimension(:,:) :: plus, minus
    real(double), dimension(3) :: dP_el, dP_ion
    real(double), dimension(3,3) :: asr
    real(double), allocatable, dimension(:,:) :: du, sdd
    real(double), allocatable, dimension(:,:,:) :: sdp, zstar, zstar_asr
    real(double) :: max_dx, max_spread, delta
    character(len=*), parameter :: sub_name = "process_bec"

    call load_runs(runs)
    n = size(runs)
    natoms = runs(1)%natoms
    do a = 1, 3
       if(runs(1)%dir(a)%nstr==0) call cq_abort("Berry phase: BEC needs the Berry phase along all "// &
            "three directions (Process.BerryDirection 0) in the reference; missing ", a)
    end do
    allocate(du(3,natoms), sdd(3,natoms), sdp(3,3,natoms), zstar(3,3,natoms), zstar_asr(3,3,natoms), &
         plus(3,natoms), minus(3,natoms))
    sdd = zero
    sdp = zero
    plus = .false.
    minus = .false.
    n_skip = 0
    n_used = 0
    write(*,fmt='(/2x,"Born effective charges by finite differences of the Berry-phase polarisation")')
    write(*,fmt='(4x,"Reference: ",a,";  displacement tolerance ",es10.3," bohr")') trim(runs(1)%label), &
         bec_disp_tol
    write(*,fmt='(/4x,"Run                                  atom  dir   delta (bohr)  max|dphase/2pi|")')
    do i = 2, n
       call delta_pol(runs(1), runs(i), dP_el, dP_ion, du, have, max_dx, max_spread)
       nmoved = count(abs(du)>bec_disp_tol)
       if(nmoved==0) then
          call cq_warn(sub_name, "Run identical to the reference, skipped: "//trim(runs(i)%label))
          n_skip = n_skip + 1
          cycle
       else if(nmoved>1) then
          write(*,fmt='(/4x,"*** Run ",a," moves ",i6," coordinates (a collective distortion).")') &
               trim(runs(i)%label), nmoved
          write(*,fmt='(4x,"*** One collective displacement gives only three equations (dP_x, dP_y, dP_z)")')
          write(*,fmt='(4x,"*** and cannot determine the 3N x 3 atomic Born effective charges, which need")')
          write(*,fmt='(4x,"*** 3N independent single-atom displacements. Use Process.Job dpo for the mode")')
          write(*,fmt='(4x,"*** effective charge of this distortion. Run skipped.")')
          call cq_warn(sub_name, "Collective distortion skipped in BEC: "//trim(runs(i)%label), nmoved)
          n_skip = n_skip + 1
          cycle
       end if
       if(.not.all(have)) call cq_abort("Berry phase: run lacks Berry phases along all three "// &
            "directions: "//trim(runs(i)%label))
       ! The one displaced coordinate
       do kk = 1, natoms
          do bb = 1, 3
             if(abs(du(bb,kk))>bec_disp_tol) then
                k = kk
                b = bb
             end if
          end do
       end do
       delta = du(b,k)
       write(*,fmt='(4x,a36,i6,i5,es15.6,f12.6)') trim(runs(i)%label), k, b, delta, max_dx
       if(max_dx>step_warn) call cq_warn(sub_name, "Large Berry-phase change for one displacement; "// &
            "use a smaller displacement. Run, max|dphase/2pi|: "//trim(runs(i)%label), max_dx)
       sdd(b,k) = sdd(b,k) + delta*delta
       sdp(:,b,k) = sdp(:,b,k) + delta*(dP_el + dP_ion)
       if(delta>zero) plus(b,k) = .true.
       if(delta<zero) minus(b,k) = .true.
       n_used = n_used + 1
    end do
    zstar = zero
    complete = .true.
    do k = 1, natoms
       do b = 1, 3
          if(sdd(b,k)>zero) then
             zstar(:,b,k) = runs(1)%volume*sdp(:,b,k)/sdd(b,k)
          else
             complete = .false.
          end if
       end do
    end do
    write(*,fmt='(/4x,"Used ",i6," displaced runs; skipped ",i6)') n_used, n_skip
    write(*,fmt='(/4x,"Born effective charge tensors Z*_ab = (Omega/e) dP_a/du_b (e);")')
    write(*,fmt='(4x,"rows a = polarisation, columns b = displacement; C = central, F = one-sided, - = missing")')
    do k = 1, natoms
       write(*,fmt='(/6x,"Atom ",i6,2x,a4,"  Z_ion ",f8.3,"   method (x,y,z): ",3(1x,a1))') k, &
            species_label(runs(1)%species(k)), runs(1)%zion(k), (method_char(plus(b,k),minus(b,k)), b=1,3)
       do a = 1, 3
          write(*,fmt='(8x,3f14.6)') zstar(a,:,k)
       end do
       write(*,fmt='(8x,"Tr/3 ",f12.6)') (zstar(1,1,k)+zstar(2,2,k)+zstar(3,3,k))/three
    end do
    zstar_asr = zstar
    if(complete) then
       do a = 1, 3
          do b = 1, 3
             asr(a,b) = sum(zstar(a,b,:))
          end do
       end do
       write(*,fmt='(/4x,"Acoustic sum rule: sum_k Z*_k (should be zero):")')
       do a = 1, 3
          write(*,fmt='(8x,3f14.6)') asr(a,:)
       end do
       write(*,fmt='(4x,"Max |sum_k Z*_k|: ",f12.6,"  (per atom: ",f12.6,")")') maxval(abs(asr)), &
            maxval(abs(asr))/real(natoms,double)
       do k = 1, natoms
          zstar_asr(:,:,k) = zstar(:,:,k) - asr/real(natoms,double)
       end do
       if(flag_bec_asr) write(*,fmt='(4x,"Process.BECApplyASR T: output files hold Z* - (1/N) sum_k Z*_k")')
    else
       call cq_warn(sub_name, "Not all atoms and directions displaced: no acoustic sum rule, "// &
            "no extended XYZ file")
    end if
    call write_bec_json(runs(1), zstar, zstar_asr, plus, minus, complete, asr)
    if(complete) then
       if(flag_bec_asr) then
          call write_bec_xyz(runs(1), zstar_asr, .true.)
       else
          call write_bec_xyz(runs(1), zstar, .false.)
       end if
    end if
    deallocate(du, sdd, sdp, zstar, zstar_asr, plus, minus, runs)
    return
  end subroutine process_bec
  !!***

  character(len=1) function method_char(plus, minus)

    implicit none

    logical, intent(in) :: plus, minus

    if(plus .and. minus) then
       method_char = 'C'
    else if(plus .or. minus) then
       method_char = 'F'
    else
       method_char = '-'
    end if
  end function method_char

  ! -----------------------------------------------------------
  ! Subroutine write_bec_xyz
  ! -----------------------------------------------------------
  !
  ! Extended XYZ in the layout of SevenNet-Polar BEC datasets:
  ! species, positions (A), born_effective_charges (9, row-major Z[pol,disp])
  !
  subroutine write_bec_xyz(ref, zstar, asr_applied)

    use numbers
    use units, only: BohrToAng
    use species_module, only: species_label
    use input_module, only: io_assign, io_close

    implicit none

    type(berry_run), intent(in) :: ref
    real(double), dimension(:,:,:), intent(in) :: zstar
    logical, intent(in) :: asr_applied

    integer :: lun, k, a
    character(len=1) :: tf

    tf = 'F'
    if(asr_applied) tf = 'T'
    call io_assign(lun)
    open(unit=lun, file='BEC_extended.xyz', status='replace')
    write(lun,'(i8)') ref%natoms
    write(lun,'(a,9f16.8,a,a,a)') 'Lattice="', ref%cell(1)*BohrToAng, zero, zero, zero, &
         ref%cell(2)*BohrToAng, zero, zero, zero, ref%cell(3)*BohrToAng, &
         '" Properties=species:S:1:pos:R:3:born_effective_charges:R:9 '// &
         'bec_tensor_convention="Z[polarization_cartesian,displacement_cartesian]" asr_corrected=', tf, &
         ' pbc="T T T"'
    do k = 1, ref%natoms
       write(lun,'(a4,3f16.8,9f14.8)') species_label(ref%species(k)), ref%pos(:,k)*BohrToAng, &
            ((zstar(a,1:3,k)), a=1,3)
    end do
    call io_close(lun)
    write(*,fmt='(4x,"Written BEC_extended.xyz")')
    return
  end subroutine write_bec_xyz

  ! -----------------------------------------------------------
  ! Subroutine write_bec_json
  ! -----------------------------------------------------------
  subroutine write_bec_json(ref, zstar, zstar_asr, plus, minus, complete, asr)

    use numbers
    use units, only: BohrToAng
    use species_module, only: species_label
    use input_module, only: io_assign, io_close

    implicit none

    type(berry_run), intent(in) :: ref
    real(double), dimension(:,:,:), intent(in) :: zstar, zstar_asr
    logical, dimension(:,:), intent(in) :: plus, minus
    logical, intent(in) :: complete
    real(double), dimension(3,3), intent(in) :: asr

    integer :: lun, k, a
    character(len=2) :: sep

    call io_assign(lun)
    open(unit=lun, file='BEC_tensors.json', status='replace')
    write(lun,'(a)') '{'
    write(lun,'(a)') '  "format": "CONQUEST PostProcessCQ BEC 1",'
    write(lun,'(a)') '  "units": {"lattice": "angstrom", "positions": "angstrom", "born_effective_charges": "e"},'
    write(lun,'(a)') '  "bec_tensor_convention": "Z[polarization_cartesian,displacement_cartesian]",'
    write(lun,'(a,a,a)') '  "reference": "', trim(ref%label), '",'
    if(complete) then
       write(lun,'(a)') '  "complete": true,'
    else
       write(lun,'(a)') '  "complete": false,'
    end if
    write(lun,'(a,3(f16.8,a))') '  "lattice": [[', ref%cell(1)*BohrToAng, ', 0.0, 0.0], [0.0, ', &
         ref%cell(2)*BohrToAng, ', 0.0], [0.0, 0.0, ', ref%cell(3)*BohrToAng, ']],'
    write(lun,'(a)') '  "atoms": ['
    do k = 1, ref%natoms
       sep = ', '
       if(k==ref%natoms) sep = '  '
       write(lun,'(a,a,a,f10.4,a,3(f16.8,a))') '    {"species": "', trim(species_label(ref%species(k))), &
            '", "z_ion": ', ref%zion(k), ', "position": [', ref%pos(1,k)*BohrToAng, ', ', &
            ref%pos(2,k)*BohrToAng, ', ', ref%pos(3,k)*BohrToAng, '],'
       write(lun,'(a,3(a,a,a))') '     "method": [', ('"',method_char(plus(a,k),minus(a,k)),'", ', a=1,2), &
            '"', method_char(plus(3,k),minus(3,k)), '"],'
       write(lun,'(a)', advance='no') '     "born_effective_charges": '
       call write_json_matrix(lun, zstar(:,:,k))
       if(complete) then
          write(lun,'(a)') ','
          write(lun,'(a)', advance='no') '     "born_effective_charges_asr": '
          call write_json_matrix(lun, zstar_asr(:,:,k))
       end if
       write(lun,'(a)') '}'//trim(sep)
    end do
    write(lun,'(a)', advance='no') '  ]'
    if(complete) then
       write(lun,'(a)') ','
       write(lun,'(a)', advance='no') '  "asr_sum": '
       call write_json_matrix(lun, asr)
    end if
    write(lun,'(/a)') '}'
    call io_close(lun)
    write(*,fmt='(4x,"Written BEC_tensors.json")')
    return
  end subroutine write_bec_json

  subroutine write_json_matrix(lun, z)

    implicit none

    integer, intent(in) :: lun
    real(double), dimension(3,3), intent(in) :: z

    write(lun,'(a,3(a,f14.8,a,f14.8,a,f14.8,a))', advance='no') '[', &
         '[', z(1,1), ', ', z(1,2), ', ', z(1,3), '], ', &
         '[', z(2,1), ', ', z(2,2), ', ', z(2,3), '], ', &
         '[', z(3,1), ', ', z(3,2), ', ', z(3,3), ']]'
    return
  end subroutine write_json_matrix

end module berry
