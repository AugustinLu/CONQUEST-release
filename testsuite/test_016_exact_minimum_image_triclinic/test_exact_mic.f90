program test_exact_mic
  use datatypes, only: double
  use global_module, only: lat_vec, lat_vec_inv, invert_3x3, mic_vector
  implicit none

  real(double) :: determinant
  real(double) :: fractional(3), displacement(3), rounded(3), brute(3)
  real(double) :: rounded_sq, exact_sq, brute_sq
  integer :: ix, iy, iz

  lat_vec(:,1) = (/ 1.0_double, 0.0_double, 0.0_double /)
  lat_vec(:,2) = (/ 0.8_double, 0.6_double, 0.0_double /)
  lat_vec(:,3) = (/ 0.0_double, 0.0_double, 1.0_double /)
  call invert_3x3(lat_vec, lat_vec_inv, determinant)

  fractional = (/ 0.49_double, 0.49_double, 0.10_double /)
  displacement = matmul(lat_vec, fractional)
  rounded = matmul(lat_vec, fractional - anint(fractional))
  rounded_sq = dot_product(rounded, rounded)
  call brute_force(displacement, 5, brute, brute_sq)
  call mic_vector(displacement)
  exact_sq = dot_product(displacement, displacement)
  call assert_close(displacement, brute, 1.0e-13_double, &
       "adversarial skew-cell displacement")
  if (exact_sq >= 0.20_double * rounded_sq) then
     error stop "test did not expose the fractional-rounding failure"
  end if

  do iz = -6, 6
     do iy = -6, 6
        do ix = -6, 6
           fractional = (/ real(ix,double)/7.0_double + 0.031_double, &
                real(iy,double)/7.0_double - 0.047_double, &
                real(iz,double)/7.0_double + 0.019_double /)
           displacement = matmul(lat_vec, fractional)
           call brute_force(displacement, 5, brute, brute_sq)
           call mic_vector(displacement)
           call assert_close(displacement, brute, 2.0e-13_double, &
                "skew-cell exhaustive comparison")
        end do
     end do
  end do

  ! The columns below span the ordinary cubic lattice but use the unimodular
  ! basis b1=a1, b2=4*a1+a2, b3=a3.
  lat_vec(:,1) = (/ 1.0_double, 0.0_double, 0.0_double /)
  lat_vec(:,2) = (/ 4.0_double, 1.0_double, 0.0_double /)
  lat_vec(:,3) = (/ 0.0_double, 0.0_double, 1.0_double /)
  call invert_3x3(lat_vec, lat_vec_inv, determinant)
  do iz = -4, 4
     do iy = -4, 4
        do ix = -4, 4
           displacement = (/ real(ix,double)/5.0_double + 0.13_double, &
                real(iy,double)/5.0_double - 0.17_double, &
                real(iz,double)/5.0_double + 0.11_double /)
           call brute_force(displacement, 9, brute, brute_sq)
           call mic_vector(displacement)
           call assert_close(displacement, brute, 2.0e-13_double, &
                "unreduced equivalent-basis comparison")
        end do
     end do
  end do

  write(*,'(a)') "PASS: exact triclinic minimum-image convention"

contains

  subroutine brute_force(input, extent, best, best_sq)
    real(double), intent(in) :: input(3)
    integer, intent(in) :: extent
    real(double), intent(out) :: best(3), best_sq
    real(double) :: trial(3), trial_sq
    integer :: i, j, k

    best = input
    best_sq = huge(1.0_double)
    do k = -extent, extent
       do j = -extent, extent
          do i = -extent, extent
             trial = input - matmul(lat_vec, real((/ i, j, k /), double))
             trial_sq = dot_product(trial, trial)
             if (trial_sq < best_sq) then
                best = trial
                best_sq = trial_sq
             end if
          end do
       end do
    end do
  end subroutine brute_force

  subroutine assert_close(actual, expected, tolerance, label)
    real(double), intent(in) :: actual(3), expected(3), tolerance
    character(*), intent(in) :: label
    if (maxval(abs(actual - expected)) > tolerance) then
       write(*,'(a,3es24.14)') "actual:   ", actual
       write(*,'(a,3es24.14)') "expected: ", expected
       error stop label
    end if
  end subroutine assert_close

end program test_exact_mic
