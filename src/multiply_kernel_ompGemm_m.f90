! -*- mode: F90; mode: font-lock -*-
! ------------------------------------------------------------------------------
! $Id$
! ------------------------------------------------------------------------------
! Module multiply_kernel
! ------------------------------------------------------------------------------
! Code area 2: matrices
! ------------------------------------------------------------------------------

!!****h* Conquest/multiply_kernel
!! NAME
!!   multiply_kernel
!! PURPOSE
!!   Contains the matrix multiplication kernel subroutines used for
!!   Conquest matrix multiplication. This is one of the hottest part
!!   of the code.
!!   |---------------------------------------------|
!!   | This is the version using GEMM library call |
!!   |---------------------------------------------|
!! AUTHOR
!!   L.Tong
!! CREATION DATE
!!   2012/08/28
!! MODIFICATION HISTORY
!! SOURCE
!!
module multiply_kernel

  character(len=*), parameter :: kernel_id = "ompGemm_m"

!!*****

contains

  !!****f* multiply_kernel/m_kern_max
  !!
  !!  NAME
  !!   m_kern_max
  !!  USAGE
  !!
  !!  PURPOSE
  !!   multiplication kernel for maximal case and reductions thereof.
  !!
  !!   nah_part:       the number of atoms in the A-halo that are contained
  !!                   in the current partition K.
  !!
  !!   kseq(k):        the unpruned sequence number of atom k in the current
  !!                   partition. `Unpruned' means that the sequence
  !!                   number counts all atoms in the partition, and not just
  !!                   those in the A-halo. The atom in question is specified
  !!                   by its `pruned' sequence number k.
  !!
  !!   k_in_part:      temporary variable for current value of kseq(k).
  !!
  !!   k_halo(.):      the A-halo sequence number of atom k. The latter is
  !!                   specified by its partition number and its pruned
  !!                   sequence number k in that partition.
  !!
  !!   k_in_halo:      temporary variable for current value of k_halo(.)
  !!
  !!   kbeg(kpart):    specifies address in k_halo(.) for start of information
  !!                   about atoms in partition kpart. The label kpart
  !!                   goes over all partitions containing atoms in the
  !!                   A-halo.
  !!
  !!   kpart:          A-halo seq. no. of current partition K
  !!
  !!   nahnab(k_in_halo):
  !!                   number of atoms in primary set that are A-neighbours of
  !!                   a given atom in the A-halo, the latter being given by its
  !!                   A-halo sequence number k_in_halo.
  !!
  !!   i_prim(.):      sequence number of atom i in primary set, this
  !!                   atom being specified as ith neighbour of atom
  !!                   k in the A-halo
  !!
  !!   ibeg(k_in_halo):
  !!                   address in i_prim(.) where index data for atom k
  !!                   start, the latter being specified by k_in_halo.
  !!
  !!   iaaddr(k_in_halo):
  !!                   address in array a where data for atom k start,
  !!                   the latter being specified by k_in_halo.
  !!
  !!   nbnab(k_in_part):
  !!                   number of B-neighbours of atom k, the latter being
  !!                   specified by its (unpruned) seq. no. in partition K.
  !!
  !!   ibaddr(k_in_part):
  !!                   address in array b where data for atom k start.
  !!
  !!   jch2cad(.):     address in array c where data for (i,j) pair start.
  !!
  !!   icad:           address in jch2cad where info for atom i starts.
  !!
  !!   jbnab2ch(.):    the C-halo seq. no. of atom j, the latter being
  !!                   specified as the jth B-neighbour of atom k.
  !!
  !!   ni_in_chalo:        total number of atoms in the C-halo.
  !!
  !!   ibpart(.):      partition to which each atom j belongs, the latter
  !!                   being specified as jth B-neighbour of atom k.
  !!
  !!   ibseq(.):       unpruned sequence number in partition for each
  !!                   atom j, the latter being specified as in ibpart.
  !!
  !!   ibindaddr(k_in_part):
  !!                   address in arrays ibpart(.) and ibseq(.) where
  !!                   data for atom k start.
  !!
  !!   k_off:          offset in partition labelling to account for p.b.c.
  !!
  !!   j_halo(.):      C-halo sequence number of atom j, the latter being
  !!                   specified in partition labelling.
  !!
  !!   jchbeg(jpart):   address in array j_halo(.) where data for
  !!                   partition jpart start.
  !!  INPUTS
  !!
  !!
  !!  USES
  !!
  !!  AUTHOR
  !!   M.J.Gillan/D.R.Bowler
  !!  CREATION DATE
  !!   25/11/99
  !!  MODIFICATION HISTORY
  !!   20/06/2001 dave
  !!    Added ROBODoc header
  !!  SOURCE
  !!
  subroutine m_kern_max(k_off, kpart, ib_nd_acc, ibaddr, nbnab,       &
                        ibpart, ibseq, bndim2, a, b, c, ahalo, chalo, &
                        at, mx_absb, mx_part, mx_iprim, lena, lenb,   &
                        lenc, debug)
    use datatypes
    use matrix_module
    use basic_types,    only: primary_set
    use primary_module, only: bundle
    use numbers,        only: zero, one

    implicit none

    ! Passed variables
    type(matrix_halo)  :: ahalo, chalo
    type(matrix_trans) :: at
    integer      :: mx_absb, mx_part, mx_iprim, lena, lenb, lenc
    integer      :: kpart, k_off
    real(double) :: a(lena)
    real(double) :: b(lenb)
    real(double) :: c(lenc)
    integer, optional :: debug
    ! Remote indices
    integer(integ), intent(in) :: ib_nd_acc(:)
    integer(integ), intent(in) :: ibaddr(:)
    integer(integ), intent(in) :: nbnab(:)
    integer(integ), intent(in) :: ibpart(:)
    integer(integ), intent(in) :: ibseq(:)
    integer(integ), intent(in) :: bndim2(:)
    ! Local variables
    integer :: jbnab2ch(mx_absb)  ! Automatic array
    integer :: nbkbeg, k, k_in_part, k_in_halo, j, jpart, jseq
    integer :: i, nabeg, i_in_prim, icad, nbbeg, j_in_halo, ncbeg
    integer :: n1, n2, n3, nb_nd_kbeg
    integer :: nd1, nd2, nd3
    integer :: naaddr, nbaddr, ncaddr
    real(double), allocatable, dimension(:,:) :: tempb, tempa, tempc
    integer :: sofar, maxnd1, maxnd2, maxnd3, maxlen
    external :: dgemm
    ! OpenMP required indexing variables
    integer :: nd1_1st(at%mx_halo), nd2_1st(mx_absb)

    ! Allocate tempa, tempb, tempc to largest possible size outside the loop
    maxnd1 = maxval(ahalo%ndimi)
    maxnd2 = maxval(bndim2)
    maxnd3 = maxval(ahalo%ndimj)
    maxlen = maxval(nbnab) * maxnd2
    allocate(tempa(maxnd1,maxnd3), tempc(maxnd1,maxlen), tempb(maxnd3,maxlen))
    tempa = zero
    tempb = zero
    tempc = zero
    ! Loop over atoms k in current A-halo partn
    do k = 1, ahalo%nh_part(kpart)
       k_in_halo = ahalo%j_beg(kpart) + k - 1
       k_in_part = ahalo%j_seq(k_in_halo)
       nbkbeg = ibaddr(k_in_part)
       nb_nd_kbeg = ib_nd_acc(k_in_part)
       nd3 = ahalo%ndimj(k_in_halo)
       ! if (PRESENT(debug)) write (21+debug,*) 'Details1: ', k, nb_nd_kbeg
       ! for OpenMP sub-array indexing
       nd1_1st(1) = 0
       do i = 2, at%n_hnab(k_in_halo)
         i_in_prim = at%i_prim(at%i_beg(k_in_halo)+i-2)
         nd1_1st(i) = nd1_1st(i-1) + nd3 * ahalo%ndimi(i_in_prim)
       end do
       nd2_1st(1) = 0
       do j = 2, nbnab(k_in_part)
          nd2_1st(j) = nd2_1st(j-1) + nd3 * bndim2(nbkbeg+j-2)
       end do
       ! transcription of j from partition to C-halo labelling
       do j = 1, nbnab(k_in_part)
          jpart = ibpart(nbkbeg+j-1) + k_off
          jseq = ibseq(nbkbeg+j-1)
          jbnab2ch(j) = chalo%i_halo(chalo%i_hbeg(jpart)+jseq-1)
       end do
!$omp do schedule(runtime)
       ! Loop over primary-set A-neighbours of k
       do i = 1, at%n_hnab(k_in_halo)
          ! nabeg = at%i_beg(k_in_halo) + i - 1
          i_in_prim = at%i_prim(at%i_beg(k_in_halo)+i-1)
          nd1 = ahalo%ndimi(i_in_prim)
          nabeg = at%i_nd_beg(k_in_halo) + nd1_1st(i)
          do n1 = 1, nd1
             naaddr = nabeg + nd3 * (n1 - 1)
             do n3 = 1, nd3
                tempa(n1,n3) = a(naaddr+n3-1)
             end do
          end do
          icad = (i_in_prim - 1) * chalo%ni_in_halo
          sofar = 0
          ! Loop over B-neighbours of atom k
          do j = 1, nbnab(k_in_part)
             nd2 = bndim2(nbkbeg+j-1)
             nbbeg = nb_nd_kbeg + nd2_1st(j)
             j_in_halo = jbnab2ch(j)
             if (j_in_halo /= 0) then
                ncbeg = chalo%i_h2d(icad+j_in_halo)
                if (ncbeg /= 0) then  ! multiplication of ndim x ndim blocks
                   ! if (present(debug)) &
                   !      write (21+debug,*) 'Details2: ', j, nd2, &
                   !                         (nabeg-1)/(nd1*nd3),  &
                   !                         (ncbeg-1)/(nd1*nd2),  &
                   !                         (nbbeg-1)/(nd2*nd3)
!DIR$ NOPATTERN
                   do n2 = 1, nd2
                      nbaddr = nbbeg + nd3 * (n2 - 1)
                      do n3 = 1, nd3
                         tempb(n3,sofar+n2) = b(nbaddr+n3-1)
                      end do
                   end do
                   sofar = sofar + nd2
                end if
             end if ! End of if (j_in_halo /= 0)
          end do ! End of j = 1, nbnab
          if (sofar > 0) then
             ! m, n, k, alpha, a, lda, b, ldb, beta, c, ldc
             call dgemm('n', 'n', nd1, sofar, nd3, one, tempa, &
                        maxnd1, tempb, maxnd3, zero, tempc, maxnd1)
          end if
          sofar = 0
          ! Loop over B-neighbours of atom k
          do j = 1, nbnab(k_in_part)
             nd2 = bndim2(nbkbeg+j-1)
             j_in_halo = jbnab2ch(j)
             if (j_in_halo /= 0) then
                ncbeg = chalo%i_h2d(icad+j_in_halo)
                if (ncbeg /= 0) then ! multiplication of ndim x ndim blocks
                   do n2 = 1, nd2
                      ncaddr = ncbeg + nd1 * (n2 - 1)
                      do n1 = 1, nd1
                         c(ncaddr+n1-1) = c(ncaddr+n1-1) + tempc(n1,sofar+n2)
                      end do
                   end do
                   sofar = sofar + nd2
                end if
             end if
          end do ! end of j = 1, nbnab(k_in_part)
       end do ! end of i = 1, at%n_hnab
!$omp end do
    end do ! end of k = 1, nahpart
    deallocate(tempa, tempb, tempc)
    return
  end subroutine m_kern_max
  !!*****


  !!****f* multiply_kernel/m_kern_min
  !!
  !!  NAME
  !!   m_kern_min
  !!  USAGE
  !!
  !!  PURPOSE
  !!   multiplication kernel for minimal case and extensions thereof.
  !!
  !!   nah_part:       the number of atoms in the A-halo that are contained
  !!                   in the current partition K.
  !!
  !!   kseq(k):        the unpruned sequence number of atom k in the current
  !!                   partition. `Unpruned' means that the sequence
  !!                   number counts all atoms in the partition, and not just
  !!                   those in the A-halo. The atom in question is specified
  !!                   by its `pruned' sequence number k.
  !!
  !!   k_in_part:      temporary variable for current value of kseq(k).
  !!
  !!   k_halo(.):      the A-halo sequence number of atom k. The latter is
  !!                   specified by its partition number and its pruned
  !!                   sequence number k in that partition.
  !!
  !!   k_in_halo:      temporary variable for current value of k_halo(.)
  !!
  !!   kbeg(kpart):    specifies address in k_halo(.) for start of information
  !!                   about atoms in partition kpart. The label kpart
  !!                   goes over all partitions containing atoms in the
  !!                   A-halo.
  !!
  !!   kpart:          A-halo seq. no. of current partition K
  !!
  !!   nahnab(k_in_halo):
  !!                   number of atoms in primary set that are A-neighbours of
  !!                   a given atom in the A-halo, the latter being given by its
  !!                   A-halo sequence number k_in_halo.
  !!
  !!   i_prim(.):      sequence number of atom i in primary set, this
  !!                   atom being specified as ith neighbour of atom
  !!                   k in the A-halo
  !!
  !!   ibeg(k_in_halo):
  !!                   address in i_prim(.) where index data for atom k
  !!                   start, the latter being specified by k_in_halo.
  !!
  !!   iaaddr(k_in_halo):
  !!                   address in array a where data for atom k start,
  !!                   the latter being specified by k_in_halo.
  !!
  !!   nbnab(k_in_part):
  !!                   number of B-neighbours of atom k, the latter being
  !!                   specified by its (unpruned) seq. no. in partition K.
  !!
  !!   ibaddr(k_in_part):
  !!                   address in array b where data for atom k start.
  !!
  !!   jch2cad(.):     address in array ! where data for (i,j) pair start.
  !!
  !!   icad:           address in jch2cad where info for atom i starts.
  !!
  !!   jbnab2ch(.):    the C-halo seq. no. of atom j, the latter being
  !!                   specified as the jth B-neighbour of atom k.
  !!
  !!   ni_in_chalo:        total number of atoms in the C-halo.
  !!
  !!   ibpart(.):      partition to which each atom j belongs, the latter
  !!                   being specified as jth B-neighbour of atom k.
  !!
  !!   ibseq(.):       unpruned sequence number in partition for each
  !!                   atom j, the latter being specified as in ibpart.
  !!
  !!   ibindaddr(k_in_part):
  !!                   address in arrays ibpart(.) and ibseq(.) where
  !!                   data for atom k start.
  !!
  !!   k_off:          offset in partition labelling to account for p.b.c.
  !!
  !!   j_halo(.):      C-halo sequence number of atom j, the latter being
  !!                   specified in partition labelling.
  !!
  !!   jchbeg(jpart):   address in array j_halo(.) where data for
  !!                   partition jpart start.
  !!  INPUTS
  !!
  !!
  !!  USES
  !!
  !!  AUTHOR
  !!   M.J.Gillan/D.R.Bowler
  !!  CREATION DATE
  !!   25/11/99
  !!  MODIFICATION HISTORY
  !!   20/06/2001 dave
  !!    Added ROBODoc header
  !!  SOURCE
  !!
  subroutine m_kern_min(k_off, kpart, ib_nd_acc, ibaddr, nbnab,       &
                        ibpart, ibseq, bndim2, a, b, c, ahalo, chalo, &
                        at, mx_absb, mx_part, mx_iprim, lena, lenb,   &
                        lenc)
    use datatypes
    use matrix_module
    use basic_types,    only: primary_set
    use primary_module, only: bundle
    use numbers,        only: one, zero

    implicit none

    ! Passed variables
    type(matrix_halo)  :: ahalo, chalo
    type(matrix_trans) :: at
    integer :: mx_absb, mx_part, mx_iprim, lena, lenb, lenc
    integer :: kpart, k_off
    ! Remember that a is a local transpose
    real(double) :: a(lena)
    real(double) :: b(lenb)
    real(double) :: c(lenc)
    ! dimension declarations
    integer(integ), intent(in) :: ib_nd_acc(:)
    integer(integ), intent(in) :: ibaddr(:)
    integer(integ), intent(in) :: nbnab(:)
    integer(integ), intent(in) :: ibpart(:)
    integer(integ), intent(in) :: ibseq(:)
    integer(integ), intent(in) :: bndim2(:)
    ! Local variables
    integer :: jbnab2ch(mx_absb)
    integer :: k, k_in_part, k_in_halo, nbkbeg, j, jpart, jseq
    integer :: i, nabeg, i_in_prim, icad, nbbeg, j_in_halo, ncbeg
    integer :: n1, n2, n3, nb_nd_kbeg
    integer :: nd1, nd2, nd3
    integer :: naaddr, nbaddr, ncaddr
    integer :: sofar, maxnd1, maxnd2, maxnd3, maxlen
    real(double), allocatable, dimension(:,:) :: tempb, tempc
    external :: dgemm
    ! OpenMP required indexing variables
    integer :: nd1_1st(at%mx_halo), nd2_1st(mx_absb)

    maxnd1 = maxval(ahalo%ndimi)
    maxnd2 = maxval(bndim2)
    maxnd3 = maxval(ahalo%ndimj)
    maxlen = maxval(nbnab) * maxnd2
    allocate(tempb(maxnd3,maxlen), tempc(maxlen,maxnd1))
    tempb = zero
    tempc = zero
    ! Loop over atoms k in current A-halo partn
    do k = 1, ahalo%nh_part(kpart)
       k_in_halo = ahalo%j_beg(kpart) + k - 1
       k_in_part = ahalo%j_seq(k_in_halo)
       nbkbeg = ibaddr(k_in_part)
       nb_nd_kbeg = ib_nd_acc(k_in_part)
       nd3 = ahalo%ndimj(k_in_halo)
       ! for OpenMP sub-array indexing
       nd1_1st(1) = 0
       do i = 2, at%n_hnab(k_in_halo)
         i_in_prim = at%i_prim(at%i_beg(k_in_halo)+i-2)
         nd1_1st(i) = nd1_1st(i-1) + nd3 * ahalo%ndimi(i_in_prim)
       end do
       nd2_1st(1) = 0
       do j = 2, nbnab(k_in_part)
          nd2_1st(j) = nd2_1st(j-1) + nd3 * bndim2(nbkbeg+j-2)
       end do
       ! transcription of j from partition to C-halo labelling
       do j = 1, nbnab(k_in_part)
          jpart = ibpart(nbkbeg+j-1) + k_off
          jseq = ibseq(nbkbeg+j-1)
          jbnab2ch(j) = chalo%i_halo(chalo%i_hbeg(jpart)+jseq-1)
       end do
!$omp do schedule(runtime)
       ! Loop over primary-set A-neighbours of k
       do i = 1, at%n_hnab(k_in_halo)
          ! nabeg = at%i_beg(k_in_halo) + i - 1
          i_in_prim = at%i_prim(at%i_beg(k_in_halo)+i-1)
          nd1 = ahalo%ndimi(i_in_prim)
          nabeg = at%i_nd_beg(k_in_halo) + nd1_1st(i)
          icad = (i_in_prim-1) * chalo%ni_in_halo
          sofar = 0
          ! Loop over B-neighbours of atom k
          do j = 1, nbnab(k_in_part)
             ! nbbeg = nbkbeg + j - 1
             nd2 = bndim2(nbkbeg+j-1)
             nbbeg = nb_nd_kbeg + nd2_1st(j)
             j_in_halo = jbnab2ch(j)
             if (j_in_halo /= 0) then
                ! nd2 = chalo%ndimj(j_in_halo)
                ncbeg = chalo%i_h2d(icad+j_in_halo)
                if (ncbeg /= 0) then ! multiplication of ndim x ndim blocks
!DIR$ NOPATTERN
                   do n2 = 1, nd2
                      nbaddr = nbbeg + nd3 * (n2 - 1)
                      ncaddr = ncbeg + nd1 * (n2 - 1)
                      do n3 = 1, nd3
                         tempb(n3,sofar+n2) = b(nbaddr+n3-1)
                      end do
                      do n1 = 1, nd1
                         tempc(sofar+n2,n1) = c(ncaddr+n1-1)
                      end do
                   end do
                   sofar = sofar + nd2
                end if
             end if
          end do
          if (sofar > 0) then
             ! m, n, k, alpha, a, lda, b, ldb, beta, c, ldc
             call dgemm('n', 'n', nd3, nd1, sofar, one, tempb, &
                        maxnd3, tempc, maxlen, one, a(nabeg:), nd3)
          end if
       end do
!$omp end do
    end do
    deallocate(tempb, tempc)
    return
  end subroutine m_kern_min
  !!*****

end module multiply_kernel

