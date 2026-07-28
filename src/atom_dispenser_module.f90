! ----------------------------------------------------------------------------------
! Module atom_dispenser_module
! ----------------------------------------------------------------------------------

!!****h* Conquest/atom_dispenser_module *
!!  NAME
!!    atom_dispenser_module
!!  PURPOSE
!!    Finds out the relations between atoms and partitions
!!  AUTHOR
!!    Michiaki Arita
!!  CREATION DATE
!!    2013/07/01
!!  MODIFICATION HISTORY
!!    Added atom2part
!!***
module atom_dispenser

  use datatypes
  use group_module, ONLY: parts
  use global_module, ONLY: flag_fractional_atomic_coords,cell_vec_len, &
                           lat_vec,lat_vec_inv, &
                           flag_MDdebug,shift_in_bohr,Iprint_MD
  use GenComms, ONLY: cq_abort

  implicit none

!!***

contains

  ! ---------------------------------------------------------------------------------
  ! Subroutine atom2part
  ! ---------------------------------------------------------------------------------

  !!****f* atom_dispenser/atom2part
  !!
  !!  NAME
  !!    atom2part
  !!  USAGE
  !!
  !!  PURPOSE
  !!    Eliminate an ambiguity in the case where atoms are on a partition
  !!    boundry. Also used in finding the partition which j-atom belongs to
  !!    at the new MD/cg step.
  !!  INPUTS
  !!
  !!  USES
  !!
  !!  AUTHOR
  !!   Michiaki Arita
  !!  CREATION DATE
  !!   2013/08/21
  !!  MODIFICATION
  !!
  !!  SOURCE
  !!
  subroutine atom2part(x,y,z,ind_part,px,py,pz,atom_id)

    ! Module usage
    use numbers
    use input_module, ONLY: io_assign, io_close
    use global_module, ONLY: io_lun
    use GenComms, ONLY: inode, ionode
    ! DB
    use io_module, ONLY: get_file_name
    use global_module, ONLY: numprocs
    use cover_module, ONLY: BCS_parts
    use dimens, ONLY: n_grid_x
    implicit none

    ! passed variables
    real(double) :: x, y, z
    integer :: px, py, pz
    integer :: ind_part, atom_id   !! NOTE: These are only for debugging. !!

    ! local variables
    integer :: i
    real(double) :: plen_x, plen_y, plen_z, px_max, px_min, py_max, py_min, &
                    pz_max, pz_min
    real(double) :: x_eps, y_eps, z_eps, eps
    real(double) :: cart(3), frac(3), eps_frac(3)
    logical :: flag_px, flag_py, flag_pz
    ! db
    integer :: lun, stat, ind_part2
    character(13) :: file_name

    !! ----------- DEBUG ----------- !!
    ! NOTE: This file will be sizable.
    if (flag_MDdebug) then
      call get_file_name('dispenser',numprocs,inode,file_name)
      call io_assign(lun)
      open (lun,file=file_name,position='append')
    endif
    !! ----------- DEBUG ----------- !!

    ! Firstly, we need to shift the atoms by eps before deciding the 
    ! partition and updating parts.
!   if (flag_fractional_atomic_coords) then
!     eps = 1.0E-08     ! May be changed later.
!   else
!     !eps = 1.0E-03    ! May be changed later.
!     eps = 1.0E-04     ! May be changed later.
!   endif
    !TM  Eps should be considered with Cartesian (bohr) units
    eps = shift_in_bohr
    cart = (/x,y,z/)
    frac = matmul(lat_vec_inv,cart)
    ! Use a positive tolerance in each fractional coordinate.  The norm
    ! of the corresponding reciprocal covector converts the historical
    ! Cartesian shift_in_bohr tolerance without assuming orthogonality.
    eps_frac(1) = eps*sqrt(sum(lat_vec_inv(1,:)**2))
    eps_frac(2) = eps*sqrt(sum(lat_vec_inv(2,:)**2))
    eps_frac(3) = eps*sqrt(sum(lat_vec_inv(3,:)**2))
    px = floor((frac(1)+eps_frac(1))*real(parts%ngcellx,double)) + 1
    py = floor((frac(2)+eps_frac(2))*real(parts%ngcelly,double)) + 1
    pz = floor((frac(3)+eps_frac(3))*real(parts%ngcellz,double)) + 1
    x_eps = frac(1)+eps_frac(1)
    y_eps = frac(2)+eps_frac(2)
    z_eps = frac(3)+eps_frac(3)
    plen_x = one/real(parts%ngcellx,double)
    plen_y = one/real(parts%ngcelly,double)
    plen_z = one/real(parts%ngcellz,double)

    ! DB
    ind_part  = (px-1) * (parts%ngcelly*parts%ngcellz) + (py-1) * parts%ngcellz + pz

    !! ----------- DEBUG ----------- !!
    if (flag_MDdebug) then
      write (lun, '(a,1x,i8)') "## Globel atom ID: ", atom_id
      write (lun, '(a,1x,l5,1x,f15.10)') "Fractional? / eps: ", flag_fractional_atomic_coords, eps
      write (lun, '(a,1x,3f15.10)') "cell lengths: ", cell_vec_len
      !write (lun, '(a,1x,3i8)') "# of parts: ", parts%ngcellx, parts%ngcelly, parts%ngcellz
      write (lun, '(a,1x,3f15.10)') "Partition lengths: ", plen_x, plen_y, plen_z
      write (lun, '(a,1x,6f15.10)') "x,y,z; x,y,z_eps: ", x, y, z, x_eps, y_eps, z_eps
      !write (lun, *) "position (x, y, z): ", x, y, z
      write (lun, '(a,1x,5i7)') "px,py,pz, ind_part: ", px, py, pz, ind_part
      write (lun, *) ""
      call io_close(lun)
    endif
    !! ----------- DEBUG ----------- !!

    return
  end subroutine atom2part
  !!***


  ! ---------------------------------------------------------------------------------
  ! Subroutine allatom2part
  ! ---------------------------------------------------------------------------------

  !!****f* atom_dispenser/allatom2part
  !!
  !!  NAME
  !!    allatom2part
  !!  USAGE
  !!
  !!  PURPOSE
  !!    Eliminates an ambiguity in the case where atoms are on a partition
  !!    boundry. Also used in finding the partition which j-atom belongs to
  !!    at the new MD/cg step. Unlike atom2part, this subroutine is called 
  !!    when updating the member information.
  !!  INPUTS
  !!    ind_part
  !!  USES
  !!    global_module,dimens
  !!  AUTHOR
  !!    Michiaki Arita 
  !!  CREATION DATE
  !!    2013/07/01
  !!  MODIFICATION
  !!
  !!  SOURCE
  !!
  subroutine allatom2part(ind_part)

    ! Module usage
    use numbers
    use GenComms, ONLY: gcopy,inode,ionode
    use global_module, ONLY: ni_in_cell,x_atom_cell,y_atom_cell,z_atom_cell, &
                             atom_coord, min_layer
    use dimens, ONLY: n_grid_x    ! DB
    use input_module, ONLY: io_assign,io_close
    use global_module, ONLY: io_lun,id_glob,numprocs

    implicit none

    ! passed variables
    integer :: ind_part(:)

    ! local variables
    integer :: n_atom,px,py,pz,i
    integer :: stat_alloc
    real(double) :: px_min,px_max,py_min,py_max,pz_min,pz_max, &
                    plen_x,plen_y,plen_z,cellx,celly,cellz
    real(double) :: x_eps,y_eps,z_eps,eps,x,y,z
    real(double) :: cart(3),frac(3),eps_frac(3)
    logical :: flag_px,flag_py,flag_pz

    ! DB
    integer :: lun,stat
    character(20) :: file_name

    if (inode.EQ.ionode .AND. Iprint_MD + min_layer > 3) &
      write (io_lun,fmt='(10x,a)') "Entering allatom2part."

    !! ---------------- DEBUG ------------------ !!
    if (flag_MDdebug .AND. inode.EQ.ionode) then
      call io_assign(lun)
      open (lun,file='allatom2part.dat',action='write',iostat=stat)
      if (stat.NE.0) call cq_abort('Error: Fail in opening allatom2part.dat .')
      write (lun,*) "No. of atoms in system:", ni_in_cell
      write (lun,*) "atom_coord(1,:)", atom_coord(1,1:)
      write (lun,*) "atom_coord(2,:)", atom_coord(2,1:)
      write (lun,*) "atom_coord(3,:)", atom_coord(3,1:)
      write (lun,*) "x_atom_cell:", x_atom_cell(1:)
      write (lun,*) "y_atom_cell:", y_atom_cell(1:)
      write (lun,*) "z_atom_cell:", z_atom_cell(1:)
      write (lun,*) ""
      call flush(lun)
    endif
    !! ---------------- DEBUG ------------------ !!

    cellx = cell_vec_len(1)
    celly = cell_vec_len(2)
    cellz = cell_vec_len(3)
    ! Firstly, we need to wrap coordinates sutisfying p.b.c.
    ! Then, we need to shift the atoms by eps before deciding the
    ! partition and updating parts.
    ! TM eps should be considered for Cartesian (bohr) units
    eps = shift_in_bohr
    ! Calculate fractional partition widths and a positive fractional
    ! boundary tolerance for the general Bravais lattice.
      plen_x = one/real(parts%ngcellx,double)
      plen_y = one/real(parts%ngcelly,double)
      plen_z = one/real(parts%ngcellz,double)
      eps_frac(1) = eps*sqrt(sum(lat_vec_inv(1,:)**2))
      eps_frac(2) = eps*sqrt(sum(lat_vec_inv(2,:)**2))
      eps_frac(3) = eps*sqrt(sum(lat_vec_inv(3,:)**2))
      if (flag_MDdebug .AND. inode.EQ.ionode) &
        write (lun,*) "plen_x,y,z:", plen_x,plen_y,plen_z !DB
      ! Get the partition (sim-cell gp (CC)) to which each atom belongs.
      flag_px=.false. ; flag_py=.false. ; flag_pz=.false.
      do n_atom = 1, ni_in_cell
        ! Wrap coordinates.
        ! NOTE: We cannot use xyz_atom_cell since they depend on parts labelling.
        cart = atom_coord(:,n_atom)
        frac = matmul(lat_vec_inv,cart)
        frac = frac-floor(frac+eps_frac)
        atom_coord(:,n_atom) = matmul(lat_vec,frac)
        x_eps = frac(1)+eps_frac(1)
        y_eps = frac(2)+eps_frac(2)
        z_eps = frac(3)+eps_frac(3)

        !! -------------- DEBUG --------------- !!
        if (flag_MDdebug .AND. inode.EQ.ionode) then
          write (lun,*) ""
          write (lun,*) "glob ID          :", n_atom
          write (lun,*) "x_eps,y_eps,z_eps:"
          write (lun,*)  x_eps,y_eps,z_eps
          write (lun,*) "atom_coord(1:3, n_atom):"
          write (lun,*) atom_coord(1,n_atom),atom_coord(2,n_atom),atom_coord(3,n_atom)
        endif
        !! -------------- DEBUG --------------- !!

        px = floor(x_eps/plen_x) + 1
        py = floor(y_eps/plen_y) + 1
        pz = floor(z_eps/plen_z) + 1
        flag_px = .true. ; flag_py = .true. ; flag_pz = .true.
        if(px <= 0 .or. px > parts%ngcellx) then
          flag_px = .false.
          write(io_lun,*) ' ERROR : flag_px , px = ',px,' x_eps, plen_x, cellx = ', x_eps, plen_x, cellx
        endif
        if(py <= 0 .or. py > parts%ngcelly) then
          flag_py = .false.
          write(io_lun,*) ' ERROR : flag_py , py = ',py,' y_eps, plen_y, celly = ', y_eps, plen_y, celly
        endif
        if(pz <= 0 .or. pz > parts%ngcellz) then
          flag_pz = .false.
          write(io_lun,*) ' ERROR : flag_pz , pz = ',pz,' z_eps, plen_z, cellz = ', z_eps, plen_z, cellz
        endif
        if(.not.flag_px .or. .not.flag_py .or. .not.flag_pz) then
          write(io_lun,*) ' flag_px, flag_py, flag_pz = ',flag_px, flag_py, flag_pz
          call cq_abort(' ERROR : flag_pxyz ',n_atom)
        endif
        ! Get the partition in sim-cell (CC).
        ind_part(n_atom) = (px-1)*(parts%ngcelly*parts%ngcellz) + (py-1)*parts%ngcellz + pz
        if (flag_MDdebug .AND. inode.EQ.ionode) &
          write (lun,*) "px,py,pz, ind_part:", px,py,pz,ind_part(n_atom) !DB
      enddo  !(n_atom, ni_in_cell)	
    if ((.NOT. flag_px) .OR. (.NOT. flag_py) .OR. (.NOT. flag_pz)) &
      call cq_abort('Error: Fail in finding partitions: allatom2part')

    !! ---------------- DEBUG ------------------ !!
    if (flag_MDdebug .AND. inode.EQ.ionode) then
      write (lun,*) ""
      write (lun,*) "ind_part(n_atom):", ind_part(1:)
      call io_close (lun)
    endif
    !! ---------------- DEBUG ------------------ !!

    return
  end subroutine allatom2part
  !!***

end module atom_dispenser
