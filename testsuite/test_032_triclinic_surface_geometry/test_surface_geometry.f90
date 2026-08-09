program test_surface_geometry
  use datatypes, only: double
  use global_module, only: lat_vec, lat_vec_inv, recip_lat_vec, cell_vol, &
       invert_3x3, lattice_face_area, lattice_plane_spacing, &
       lattice_normal_coordinate
  implicit none

  real(double) :: fractional(3), point(3), expected_area, expected_height
  real(double) :: face_vector(3), determinant
  integer :: i, j, k

  lat_vec(:,1) = (/ 4.0_double, 1.0_double, 0.5_double /)
  lat_vec(:,2) = (/ 1.0_double, 3.0_double, 0.2_double /)
  lat_vec(:,3) = (/ 0.5_double, 0.7_double, 5.0_double /)
  call invert_3x3(lat_vec,lat_vec_inv,determinant)
  cell_vol = determinant
  recip_lat_vec = transpose(lat_vec_inv)

  fractional = (/ -0.20_double, 1.30_double, 0.40_double /)
  point = matmul(lat_vec,fractional)

  do i = 1, 3
     select case(i)
     case(1)
        j = 2; k = 3
     case(2)
        j = 3; k = 1
     case default
        j = 1; k = 2
     end select
     face_vector = cross_product(lat_vec(:,j),lat_vec(:,k))
     expected_area = sqrt(dot_product(face_vector,face_vector))
     expected_height = abs(cell_vol)/expected_area
     call assert_close(lattice_face_area(i),expected_area,"face area")
     call assert_close(lattice_plane_spacing(i),expected_height,"plane spacing")
     call assert_close(lattice_normal_coordinate(point,i), &
          modulo(fractional(i),1.0_double)*expected_height, &
          "wrapped normal coordinate")
  end do

  write(*,'(a)') "PASS: triclinic surface areas, heights, and coordinates"

contains

  function cross_product(a,b) result(c)
    real(double), intent(in) :: a(3), b(3)
    real(double) :: c(3)
    c = (/ a(2)*b(3)-a(3)*b(2), &
           a(3)*b(1)-a(1)*b(3), &
           a(1)*b(2)-a(2)*b(1) /)
  end function cross_product

  subroutine assert_close(actual,expected,label)
    real(double), intent(in) :: actual, expected
    character(*), intent(in) :: label
    if (abs(actual-expected) > 1.0e-12_double) then
       write(*,'(a,es24.14)') "actual:   ", actual
       write(*,'(a,es24.14)') "expected: ", expected
       error stop label
    end if
  end subroutine assert_close

end program test_surface_geometry
