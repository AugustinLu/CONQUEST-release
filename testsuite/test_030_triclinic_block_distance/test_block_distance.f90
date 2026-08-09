program test_block_distance
  use datatypes, only: double
  use global_module, only: point_parallelepiped_distance_sq
  implicit none

  real(double) :: point(3), origin(3), edges(3,3), distance_sq

  origin = 0.0_double
  edges = 0.0_double
  edges(:,1) = (/ 2.0_double, 0.0_double, 0.0_double /)
  edges(:,2) = (/ 0.0_double, 3.0_double, 0.0_double /)
  edges(:,3) = (/ 0.0_double, 0.0_double, 4.0_double /)
  point = (/ 3.0_double, -1.0_double, 2.0_double /)
  distance_sq = point_parallelepiped_distance_sq(point,origin,edges)
  call assert_close(distance_sq,2.0_double,"axis-aligned control")

  ! This point is inside the Cartesian AABB of a highly skewed block, but
  ! outside the block itself.  The exact distance is 64/65; the retired AABB
  ! approximation returned zero and forced unrelated covering-set padding.
  edges(:,1) = (/ 1.0_double, 0.0_double, 0.0_double /)
  edges(:,2) = (/ 8.0_double, 1.0_double, 0.0_double /)
  edges(:,3) = (/ 0.0_double, 0.0_double, 1.0_double /)
  point = (/ 0.0_double, 1.0_double, 0.5_double /)
  distance_sq = point_parallelepiped_distance_sq(point,origin,edges)
  call assert_close(distance_sq,64.0_double/65.0_double, &
       "extreme-skew AABB false positive")

  point = origin + matmul(edges, &
       (/ 0.25_double, 0.75_double, 0.40_double /))
  distance_sq = point_parallelepiped_distance_sq(point,origin,edges)
  call assert_close(distance_sq,0.0_double,"interior point")

  point = origin + matmul(edges, &
       (/ 0.25_double, 0.75_double, 1.0_double /)) + &
       (/ 0.0_double, 0.0_double, 2.0_double /)
  distance_sq = point_parallelepiped_distance_sq(point,origin,edges)
  call assert_close(distance_sq,4.0_double,"normal face projection")

  write(*,'(a)') "PASS: exact point-to-triclinic-block distance"

contains

  subroutine assert_close(actual, expected, label)
    real(double), intent(in) :: actual, expected
    character(*), intent(in) :: label
    if (abs(actual-expected) > 1.0e-12_double) then
       write(*,'(a,es24.14)') "actual:   ", actual
       write(*,'(a,es24.14)') "expected: ", expected
       error stop label
    end if
  end subroutine assert_close

end program test_block_distance
