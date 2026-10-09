! Geometry and constraints for the fixed-angle cell-length coordinates used
! by Methods 1 and 2. The physical Cartesian virial is never modified here.
module cell_relaxation
  use datatypes, only: double
  implicit none
  private
  public :: length_gradient, project_length_gradient
contains
  pure subroutine length_gradient(lattice, inverse, lengths, virial, pressure_volume, gradient)
    real(double), intent(in) :: lattice(3,3), inverse(3,3), lengths(3)
    real(double), intent(in) :: virial(3,3), pressure_volume
    real(double), intent(out) :: gradient(3)
    integer :: i, j, k
    ! dA/dL_i = a_i/L_i. Thus dH/dL_i =
    ! [sigma : (a_i tensor row_i(A^-1)) + p V] / L_i.
    ! A unit-vector quadratic projection would describe a different strain.
    do i=1,3
       gradient(i) = pressure_volume
       do j=1,3
          do k=1,3
             gradient(i) = gradient(i) + virial(j,k)*lattice(j,i)*inverse(i,k)
          end do
       end do
       gradient(i) = gradient(i)/lengths(i)
    end do
  end subroutine length_gradient

  pure subroutine project_length_gradient(gradient, lengths, constraint)
    real(double), intent(inout) :: gradient(3)
    real(double), intent(in) :: lengths(3)
    character(len=*), intent(in) :: constraint
    character(len=len(constraint)) :: flag
    real(double) :: ratio
    integer :: i, code
    flag = adjustl(constraint)
    do i=1,len_trim(flag)
       code = iachar(flag(i:i))
       if (code >= iachar('A') .and. code <= iachar('Z')) flag(i:i) = achar(code+32)
    end do
    select case(trim(flag))
    case('a')
       gradient(1) = 0.0_double
    case('b')
       gradient(2) = 0.0_double
    case('c')
       gradient(3) = 0.0_double
    case('a b','b a')
       gradient(1:2) = 0.0_double
    case('a c','c a')
       gradient(1) = 0.0_double
       gradient(3) = 0.0_double
    case('b c','c b')
       gradient(2:3) = 0.0_double
    case('volume')
       gradient = sum(gradient)/3.0_double
    case('a/b','b/a')
       ratio = lengths(2)/lengths(1)
       gradient(1) = (gradient(1)+gradient(2))/(1.0_double+ratio)
       gradient(2) = ratio*gradient(1)
    case('a/c','c/a')
       ratio = lengths(3)/lengths(1)
       gradient(1) = (gradient(1)+gradient(3))/(1.0_double+ratio)
       gradient(3) = ratio*gradient(1)
    case('b/c','c/b')
       ratio = lengths(3)/lengths(2)
       gradient(2) = (gradient(2)+gradient(3))/(1.0_double+ratio)
       gradient(3) = ratio*gradient(2)
    end select
  end subroutine project_length_gradient
end module cell_relaxation
