! -*- mode: F90; mode: font-lock -*-
! ------------------------------------------------------------------------------
! $Id$
! ------------------------------------------------------------------------------
! Conquest: O(N) DFT
! ------------------------------------------------------------------------------

!!****m* Conquest/bec_module *
!!
!!  NAME
!!   bec_module
!!  PURPOSE
!!   Contains routines to compute the Born Effective Charge (BEC) tensor
!!  AUTHOR
!!   Conquest developers
!!  CREATION DATE
!!   2024
!!  MODIFICATION HISTORY
!!
!!  SOURCE
!!
module bec_module

  use datatypes
  use numbers

  implicit none

contains

  !!****f* bec_module/bec_run *
  !!
  !!  NAME
  !!   bec_run
  !!  PURPOSE
  !!   Calculates the Born Effective Charge (BEC) tensor using central
  !!   finite differences.
  !!  INPUTS
  !!   fixed_potential - logical to fix potential
  !!   vary_mu         - logical to vary chemical potential
  !!   total_energy    - total energy of the system
  !!  AUTHOR
  !!   Conquest developers
  !!  CREATION DATE
  !!   2024
  !!  SOURCE
  !!
  subroutine bec_run(fixed_potential, vary_mu, total_energy)

    use dimens,           only: r_super_x, r_super_y, r_super_z
    use global_module,    only: ni_in_cell, atom_coord, flag_calc_pol, &
                                bec_disp, io_lun, iprint_gen, bec_tensor, &
                                flag_calc_bec, ne_in_cell, species_glob, flag_LmatrixReuse, flag_DM_converged, restart_DM
    use polarisation,     only: get_polarisation, Pel_gamma, get_P_ionic
    use minimise,         only: get_E_and_F
    use GenComms,         only: inode, ionode, cq_abort, my_barrier
    use io_module,        only: write_extxyz
    use force_module,     only: tot_force, stress
    use species_module,   only: species_label
    use move_atoms,       only: update_pos_and_matrices, update_H, update_r_atom_cell

    implicit none

    ! Passed variables
    logical, intent(inout)      :: fixed_potential
    logical, intent(inout)      :: vary_mu
    real(double), intent(inout) :: total_energy

    ! Local variables
    integer :: i, j, k
    real(double), allocatable, dimension(:,:) :: r_orig
    real(double), dimension(3) :: p_plus, p_minus, p_diff
    real(double), dimension(3) :: cell_vec
    real(double) :: cell_vol
    real(double) :: quantum_val(3)
    real(double), dimension(3) :: p_ionic_plus, p_ionic_minus
    logical :: flag_LmatrixReuse_orig
    logical :: flag_DM_converged_orig

    if (.not. allocated(bec_tensor)) allocate(bec_tensor(3,3,ni_in_cell))
    bec_tensor = zero
    allocate(r_orig(3,ni_in_cell))

    cell_vec(1) = r_super_x
    cell_vec(2) = r_super_y
    cell_vec(3) = r_super_z
    cell_vol = r_super_x * r_super_y * r_super_z
    quantum_val = cell_vec / cell_vol

    ! Save original coords
    r_orig = atom_coord

    if (inode == ionode) then
       write(io_lun, fmt='(/,4x,60("-"))')
       write(io_lun, fmt='(4x,"Born Effective Charge (BEC) Calculation via Finite Diff")')
       write(io_lun, fmt='(4x,"Displacement amplitude (Bohr): ", f10.6)') bec_disp
       write(io_lun, fmt='(4x,60("-"),/)')
    end if

    flag_LmatrixReuse_orig = flag_LmatrixReuse
    flag_LmatrixReuse = .false.
    flag_DM_converged_orig = flag_DM_converged
    flag_DM_converged = .false.


    ! Base calculation (Optional but helps converge DM)
    if (inode == ionode) write(io_lun, fmt='(4x,"Calculating ground state...")')
    flag_DM_converged = .false.
          restart_DM = .false.
          call get_E_and_F(fixed_potential, vary_mu, total_energy, .true., .true., 0)

    ! Loop over atoms and coordinates
    do i = 1, ni_in_cell
       do j = 1, 3
          if (inode == ionode) write(io_lun, fmt='(/,4x,"Atom ", i5, " disp direction ", i1)') i, j

          ! Plus displacement
          atom_coord(j, i) = r_orig(j, i) + bec_disp
          if (inode == ionode) write(io_lun, fmt='(6x,"Plus displacement...")')
          call update_r_atom_cell()
          call update_pos_and_matrices(0)
          call update_H(fixed_potential)
          flag_DM_converged = .false.
          restart_DM = .false.
          call get_E_and_F(fixed_potential, vary_mu, total_energy, .true., .true., 0)
          call get_polarisation()
          call get_P_ionic(p_ionic_plus)
          ! P = P_el + P_ion. We use cell_vec / cell_vol to convert to standard units
          ! But for BEC Z* = V * dP / dU = V * (P_plus - P_minus) / (2d) * (quantum_scale)
          ! Let's get total P in fractional coordinates first (quantum = 1).
          p_plus = Pel_gamma + p_ionic_plus

          ! Minus displacement
          atom_coord(j, i) = r_orig(j, i) - bec_disp
          if (inode == ionode) write(io_lun, fmt='(6x,"Minus displacement...")')
          call update_r_atom_cell()
          call update_pos_and_matrices(0)
          call update_H(fixed_potential)
          flag_DM_converged = .false.
          restart_DM = .false.
          call get_E_and_F(fixed_potential, vary_mu, total_energy, .true., .true., 0)
          call get_polarisation()
          call get_P_ionic(p_ionic_minus)
          p_minus = Pel_gamma + p_ionic_minus

          ! Restore atom
          atom_coord(j, i) = r_orig(j, i)
          call update_r_atom_cell()
          call update_pos_and_matrices(0)
          call update_H(fixed_potential)

          ! Calculate difference and unwrap phase
          do k = 1, 3
             p_diff(k) = p_plus(k) - p_minus(k)
             ! Unwrap phase difference to be in [-0.5, 0.5] (since quantum=1 in frac coords)
             p_diff(k) = p_diff(k) - nint(p_diff(k))

             ! Z*_{i, kj} = V * dP_k / dU_j
             ! Here p_diff is in frac coords. To get physical P change: p_diff_phys = p_diff_frac * cell_vec / V
             ! So dP_k = p_diff(k) * cell_vec(k) / V
             ! Z* = V * (p_diff(k) * cell_vec(k) / V) / (2 * bec_disp)
             ! Z* = p_diff(k) * cell_vec(k) / (2 * bec_disp)
             bec_tensor(k, j, i) = p_diff(k) * cell_vec(k) / (2.0_double * bec_disp)
          end do

          if (inode == ionode) then
             write(io_lun, fmt='(6x,"Z*_x = ", f12.6, " Z*_y = ", f12.6, " Z*_z = ", f12.6)') &
                   bec_tensor(1, j, i), bec_tensor(2, j, i), bec_tensor(3, j, i)
          end if

       end do
    end do

    if (inode == ionode) then
       write(io_lun, fmt='(/,4x,60("-"))')
       write(io_lun, fmt='(4x,"Born Effective Charge (BEC) Tensors:")')
       write(io_lun, fmt='(4x,60("-"))')
       do i = 1, ni_in_cell
          write(io_lun, fmt='(4x,"Atom ", i5, " (", a, ")")') i, adjustr(species_label(species_glob(i))(1:2))
          write(io_lun, fmt='(6x,"Z*_xx: ", f10.5, " Z*_xy: ", f10.5, " Z*_xz: ", f10.5)') &
                bec_tensor(1,1,i), bec_tensor(1,2,i), bec_tensor(1,3,i)
          write(io_lun, fmt='(6x,"Z*_yx: ", f10.5, " Z*_yy: ", f10.5, " Z*_yz: ", f10.5)') &
                bec_tensor(2,1,i), bec_tensor(2,2,i), bec_tensor(2,3,i)
          write(io_lun, fmt='(6x,"Z*_zx: ", f10.5, " Z*_zy: ", f10.5, " Z*_zz: ", f10.5)') &
                bec_tensor(3,1,i), bec_tensor(3,2,i), bec_tensor(3,3,i)
       end do
       write(io_lun, fmt='(4x,60("-"),/)')
    end if

    ! Output to XYZ if write_extxyz is called by main logic
    ! Actually, write_extxyz is usually called from control_run. We will call it here.
    flag_LmatrixReuse = flag_LmatrixReuse_orig
    flag_DM_converged = flag_DM_converged_orig
    call write_extxyz('trajectory.xyz', total_energy, tot_force, stress)

    deallocate(r_orig)

  end subroutine bec_run

end module bec_module
