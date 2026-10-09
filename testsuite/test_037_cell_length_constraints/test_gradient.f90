program test_gradient
  use datatypes, only: double
  use cell_relaxation, only: length_gradient, project_length_gradient
  implicit none
  real(double) :: a(3,3), inv(3,3), lengths(3), virial(3,3), grad(3), raw(3)
  real(double) :: rot(3,3), rotated(3,3), other(3), plus(3,3), minus(3,3), fd, step, volume
  integer :: i
  a(:,1) = [2.0_double,0.4_double,0.2_double]
  a(:,2) = [-0.8_double,2.4_double,0.3_double]
  a(:,3) = [0.5_double,-0.2_double,3.1_double]
  lengths = sqrt(sum(a*a,dim=1))
  call inverse(a,inv,volume)
  virial = matmul(matmul(a,matmul(transpose(a),a)),transpose(a))
  call length_gradient(a,inv,lengths,virial,0.2_double*volume,grad)
  raw = grad
  step = 1.e-5_double
  do i=1,3
     plus = a
     minus = a
     plus(:,i) = a(:,i)*(1.0_double+step/lengths(i))
     minus(:,i) = a(:,i)*(1.0_double-step/lengths(i))
     fd = (energy(plus)-energy(minus))/(2*step)
     if (abs(fd-grad(i)) > 1.e-7_double) stop 1
  end do
  ! Rotate around an arbitrary axis (cyclic permutation plus a planar rotation).
  rot(:,1) = [0.0_double,0.8_double,0.6_double]
  rot(:,2) = [0.0_double,-0.6_double,0.8_double]
  rot(:,3) = [1.0_double,0.0_double,0.0_double]
  rotated = matmul(rot,a)
  call length_gradient(rotated,matmul(inv,transpose(rot)),lengths, &
       matmul(matmul(rot,virial),transpose(rot)),0.2_double*volume,other)
  if (maxval(abs(other-grad)) > 1.e-12_double) stop 2
  call project_length_gradient(grad,lengths,'a')
  if (grad(1) /= 0.0_double .or. any(grad(2:3) /= raw(2:3))) stop 3
  grad = raw
  call project_length_gradient(grad,lengths,'B C')
  if (grad(1) /= raw(1) .or. any(grad(2:3) /= 0.0_double)) stop 4
  ! Nonzero target pressure must also disappear in the frozen coordinates.
  call length_gradient(a,inv,lengths,0.0_double*virial,0.2_double*volume,grad)
  call project_length_gradient(grad,lengths,'a b')
  if (any(grad(1:2) /= 0.0_double)) stop 5
  print *, 'PASS: finite differences, rotation covariance, fixed lengths, target pressure'
contains
  subroutine inverse(x,y,det)
    real(double), intent(in) :: x(3,3)
    real(double), intent(out) :: y(3,3), det
    y(1,:) = cross(x(:,2),x(:,3))
    y(2,:) = cross(x(:,3),x(:,1))
    y(3,:) = cross(x(:,1),x(:,2))
    det = sum(x(:,1)*y(1,:))
    y = y/det
  end subroutine
  function cross(x,y) result(z)
    real(double), intent(in) :: x(3),y(3)
    real(double) :: z(3)
    z = [x(2)*y(3)-x(3)*y(2), x(3)*y(1)-x(1)*y(3), x(1)*y(2)-x(2)*y(1)]
  end function
  function energy(x) result(e)
    real(double), intent(in) :: x(3,3)
    real(double) :: e, metric(3,3), unused(3,3), det
    metric = matmul(transpose(x),x)
    call inverse(x,unused,det)
    e = 0.25_double*sum(metric*metric)+0.2_double*det
  end function
end program
