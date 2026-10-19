! -*- mode: F90; mode: font-lock -*-
! ------------------------------------------------------------------------------
! Module: cuda_module
! ------------------------------------------------------------------------------
! CONQUEST CUDA GPU Acceleration Module
! Provides Fortran 2003 iso_c_binding interfaces to the dynamic C-ABI CUDA bridge.
! ------------------------------------------------------------------------------
module cuda_module
  use, intrinsic :: iso_c_binding
  use datatypes, only: double, double_cplx
  use mpi, only: MPI_COMM_WORLD
  !$ use omp_lib, only: omp_in_parallel
  implicit none

  private

  ! Public configuration flags and parameters
  public :: flag_use_cuda, flag_cuda_ready
  public :: cuda_diag_min_n, cuda_diag_max_n, cuda_gemm_min_flops, cuda_fft3d_min_n, cuda_in_parallel
  public :: conquest_cuda_init, conquest_cuda_finalize, conquest_cuda_set_device_hint
  public :: conquest_cusolver_zhegv
  public :: conquest_cublas_dgemm, conquest_cublas_zgemm
  public :: conquest_cufft_3d_z2z

  logical, save :: flag_use_cuda = .true.
  logical, save :: flag_cuda_ready = .false.

  ! Minimum problem sizes for offloading (break-even points measured on a
  ! Quadro RTX 5000 / Ryzen 7 5700X, PCIe transfers and WDDM latency included).
  ! Override with CONQUEST_CUDA_MIN_N, CONQUEST_CUDA_MIN_FLOPS, CONQUEST_CUDA_MIN_FFT.
  ! GEMM offload is off by default: FP64 cuBLAS only matched 8 CPU threads at
  ! 4000^3 and lost when several MPI ranks shared the GPU. 1e9 is the
  ! single-thread break-even if you want to try it (CONQUEST_CUDA_MIN_FLOPS=1e9).
  integer, save :: cuda_diag_min_n = 200
  ! The legacy cuSOLVER zhegvd API takes 32-bit sizes, so N*N must stay below 2^31
  integer, parameter :: cuda_diag_max_n = 46340
  real(double), save :: cuda_gemm_min_flops = 1.0e30_double
  integer, save :: cuda_fft3d_min_n = 48
  ! GEMM/FFT calls made from inside an active OpenMP team would only queue on the
  ! single GPU lock while the other threads idle, so by default they stay on the CPU.
  ! Set CONQUEST_CUDA_IN_PARALLEL=1 to offload them anyway.
  logical, save :: cuda_in_parallel = .false.

  ! C-ABI function interfaces
  interface
     function c_cq_cuda_init(myid, dev_count) bind(C, name="cq_cuda_init")
       use, intrinsic :: iso_c_binding
       integer(c_int), value :: myid
       type(c_ptr), value :: dev_count
       integer(c_int) :: c_cq_cuda_init
     end function c_cq_cuda_init

     subroutine c_cq_cuda_finalize() bind(C, name="cq_cuda_finalize")
       use, intrinsic :: iso_c_binding
     end subroutine c_cq_cuda_finalize

     subroutine c_cq_cuda_set_device_hint(hint) bind(C, name="cq_cuda_set_device_hint")
       use, intrinsic :: iso_c_binding
       integer(c_int), value :: hint
     end subroutine c_cq_cuda_set_device_hint

     function c_cq_cuda_is_available() bind(C, name="cq_cuda_is_available")
       use, intrinsic :: iso_c_binding
       integer(c_int) :: c_cq_cuda_is_available
     end function c_cq_cuda_is_available

     function c_cq_cusolver_zhegv(mode_v, n, h_A, lda, h_B, ldb, h_W) bind(C, name="cq_cusolver_zhegv")
       use, intrinsic :: iso_c_binding
       integer(c_int), value :: mode_v
       integer(c_int), value :: n
       type(c_ptr), value :: h_A
       integer(c_int), value :: lda
       type(c_ptr), value :: h_B
       integer(c_int), value :: ldb
       type(c_ptr), value :: h_W
       integer(c_int) :: c_cq_cusolver_zhegv
     end function c_cq_cusolver_zhegv

     function c_cq_cublas_dgemm(op_a, op_b, m, n, k, alpha, h_A, lda, h_B, ldb, beta, h_C, ldc) &
          bind(C, name="cq_cublas_dgemm")
       use, intrinsic :: iso_c_binding
       integer(c_int), value :: op_a, op_b
       integer(c_int), value :: m, n, k
       real(c_double), value :: alpha
       type(c_ptr), value :: h_A
       integer(c_int), value :: lda
       type(c_ptr), value :: h_B
       integer(c_int), value :: ldb
       real(c_double), value :: beta
       type(c_ptr), value :: h_C
       integer(c_int), value :: ldc
       integer(c_int) :: c_cq_cublas_dgemm
     end function c_cq_cublas_dgemm

     function c_cq_cublas_zgemm(op_a, op_b, m, n, k, alpha, h_A, lda, h_B, ldb, beta, h_C, ldc) &
          bind(C, name="cq_cublas_zgemm")
       use, intrinsic :: iso_c_binding
       integer(c_int), value :: op_a, op_b
       integer(c_int), value :: m, n, k
       type(c_ptr), value :: alpha
       type(c_ptr), value :: h_A
       integer(c_int), value :: lda
       type(c_ptr), value :: h_B
       integer(c_int), value :: ldb
       type(c_ptr), value :: beta
       type(c_ptr), value :: h_C
       integer(c_int), value :: ldc
       integer(c_int) :: c_cq_cublas_zgemm
     end function c_cq_cublas_zgemm

     function c_cq_cufft_3d_z2z(nx, ny, nz, h_data, isign) bind(C, name="cq_cufft_3d_z2z")
       use, intrinsic :: iso_c_binding
       integer(c_int), value :: nx, ny, nz
       type(c_ptr), value :: h_data
       integer(c_int), value :: isign
       integer(c_int) :: c_cq_cufft_3d_z2z
     end function c_cq_cufft_3d_z2z
  end interface

contains

  subroutine conquest_cuda_init(myid)
    integer, intent(in) :: myid
    character(len=32) :: env_val
    integer(c_int), target :: dev_count
    integer :: rc, stat
    real(double) :: rflops

    ! Check if user disabled CUDA explicitly via environment variable
    call get_environment_variable("CONQUEST_USE_CUDA", env_val, status=stat)
    if (stat == 0) then
       read(env_val, *, iostat=stat) rc
       if (stat == 0 .and. rc == 0) then
          flag_use_cuda = .false.
          flag_cuda_ready = .false.
          return
       end if
    end if

    ! Check environment variable overrides for minimum sizes
    call get_environment_variable("CONQUEST_CUDA_MIN_N", env_val, status=stat)
    if (stat == 0) then
       read(env_val, *, iostat=stat) rc
       if (stat == 0 .and. rc >= 1) cuda_diag_min_n = rc
    end if

    call get_environment_variable("CONQUEST_CUDA_MIN_FLOPS", env_val, status=stat)
    if (stat == 0) then
       read(env_val, *, iostat=stat) rflops
       if (stat == 0 .and. rflops >= 0.0_double) cuda_gemm_min_flops = rflops
    end if

    call get_environment_variable("CONQUEST_CUDA_IN_PARALLEL", env_val, status=stat)
    if (stat == 0) then
       read(env_val, *, iostat=stat) rc
       if (stat == 0) cuda_in_parallel = (rc /= 0)
    end if

    call get_environment_variable("CONQUEST_CUDA_MIN_FFT", env_val, status=stat)
    if (stat == 0) then
       read(env_val, *, iostat=stat) rc
       if (stat == 0 .and. rc >= 1) cuda_fft3d_min_n = rc
    end if

    dev_count = 0
    rc = c_cq_cuda_init(int(myid, c_int), c_loc(dev_count))
    if (rc /= 0) then
       flag_cuda_ready = .true.
    else
       flag_cuda_ready = .false.
    end if
  end subroutine conquest_cuda_init

  ! Suggest which GPU this process should use (taken modulo the number of
  ! visible devices). Only effective before the process first uses the GPU.
  subroutine conquest_cuda_set_device_hint(hint)
    integer, intent(in) :: hint
    if (flag_cuda_ready) call c_cq_cuda_set_device_hint(int(hint, c_int))
  end subroutine conquest_cuda_set_device_hint

  subroutine conquest_cuda_finalize()
    if (flag_cuda_ready) then
       call c_cq_cuda_finalize()
       flag_cuda_ready = .false.
    end if
  end subroutine conquest_cuda_finalize

  ! Fortran wrapper for generalized Hermitian eigensolver
  subroutine conquest_cusolver_zhegv(mode, n, A, lda, B, ldb, W, info)
    character(len=1), intent(in) :: mode
    integer, intent(in) :: n, lda, ldb
    complex(double_cplx), intent(inout), target :: A(lda, n)
    complex(double_cplx), intent(inout), target :: B(ldb, n)
    real(double), intent(out), target :: W(n)
    integer, intent(out) :: info

    integer(c_int) :: mode_v, rc

    if (.not. flag_cuda_ready .or. .not. flag_use_cuda .or. n < cuda_diag_min_n .or. n > cuda_diag_max_n) then
       info = -999 ! Signal caller to fall back to ScaLAPACK / LAPACK
       return
    end if

    mode_v = 0_c_int
    if (mode == 'V' .or. mode == 'v') mode_v = 1_c_int

    rc = c_cq_cusolver_zhegv(mode_v, int(n, c_int), c_loc(A), int(lda, c_int), &
                             c_loc(B), int(ldb, c_int), c_loc(W))
    call check_partial_copy(rc, 'zhegvd')
    info = int(rc)
  end subroutine conquest_cusolver_zhegv

  ! Fortran wrapper for cuBLAS DGEMM
  subroutine conquest_cublas_dgemm(transa, transb, m, n, k, alpha, A, lda, B, ldb, beta, C, ldc, ierr)
    character(len=1), intent(in) :: transa, transb
    integer, intent(in) :: m, n, k, lda, ldb, ldc
    real(double), intent(in) :: alpha, beta
    real(double), intent(in), target :: A(*)
    real(double), intent(in), target :: B(*)
    real(double), intent(inout), target :: C(*)
    integer, intent(out) :: ierr

    integer(c_int) :: rc
    real(double) :: total_flops

    total_flops = 2.0_double * real(m, double) * real(n, double) * real(k, double)
    if (.not. flag_cuda_ready .or. .not. flag_use_cuda .or. total_flops < cuda_gemm_min_flops &
        .or. in_omp_team()) then
       ierr = -999
       return
    end if

    rc = c_cq_cublas_dgemm(map_op(transa), map_op(transb), int(m, c_int), int(n, c_int), int(k, c_int), &
                           real(alpha, c_double), c_loc(A), int(lda, c_int), &
                           c_loc(B), int(ldb, c_int), &
                           real(beta, c_double), c_loc(C), int(ldc, c_int))
    call check_partial_copy(rc, 'dgemm')
    ierr = int(rc)
  end subroutine conquest_cublas_dgemm

  ! Fortran wrapper for cuBLAS ZGEMM
  subroutine conquest_cublas_zgemm(transa, transb, m, n, k, alpha, A, lda, B, ldb, beta, C, ldc, ierr)
    character(len=1), intent(in) :: transa, transb
    integer, intent(in) :: m, n, k, lda, ldb, ldc
    complex(double_cplx), intent(in), target :: alpha, beta
    complex(double_cplx), intent(in), target :: A(*)
    complex(double_cplx), intent(in), target :: B(*)
    complex(double_cplx), intent(inout), target :: C(*)
    integer, intent(out) :: ierr

    integer(c_int) :: rc
    real(double) :: total_flops

    total_flops = 8.0_double * real(m, double) * real(n, double) * real(k, double)
    if (.not. flag_cuda_ready .or. .not. flag_use_cuda .or. total_flops < cuda_gemm_min_flops &
        .or. in_omp_team()) then
       ierr = -999
       return
    end if

    rc = c_cq_cublas_zgemm(map_op(transa), map_op(transb), int(m, c_int), int(n, c_int), int(k, c_int), &
                           c_loc(alpha), c_loc(A), int(lda, c_int), &
                           c_loc(B), int(ldb, c_int), &
                           c_loc(beta), c_loc(C), int(ldc, c_int))
    call check_partial_copy(rc, 'zgemm')
    ierr = int(rc)
  end subroutine conquest_cublas_zgemm

  function map_op(c) result(op)
    character(len=1), intent(in) :: c
    integer(c_int) :: op
    if (c == 'T' .or. c == 't') then
       op = 1_c_int
    else if (c == 'C' .or. c == 'c') then
       op = 2_c_int
    else
       op = 0_c_int
    end if
  end function map_op

  ! Fortran wrapper for cuFFT 3D Z2Z
  subroutine conquest_cufft_3d_z2z(nx, ny, nz, cdata, isign, ierr)
    integer, intent(in) :: nx, ny, nz, isign
    complex(double_cplx), intent(inout), target :: cdata(nx, ny, nz)
    integer, intent(out) :: ierr

    integer(c_int) :: rc

    if (.not. flag_cuda_ready .or. .not. flag_use_cuda .or. &
        min(nx, min(ny, nz)) < cuda_fft3d_min_n .or. in_omp_team()) then
       ierr = -999
       return
    end if

    rc = c_cq_cufft_3d_z2z(int(nx, c_int), int(ny, c_int), int(nz, c_int), &
                           c_loc(cdata), int(isign, c_int))
    call check_partial_copy(rc, 'fft')
    ierr = int(rc)
  end subroutine conquest_cufft_3d_z2z

  ! True when called from inside an OpenMP team of more than one thread
  logical function in_omp_team()
    in_omp_team = .false.
    !$ if (.not. cuda_in_parallel) in_omp_team = omp_in_parallel()
  end function in_omp_team

  ! A failure while copying results back leaves the output array partially
  ! overwritten, so a CPU fallback is no longer possible: stop the run.
  subroutine check_partial_copy(rc, routine)
    integer(c_int), intent(in) :: rc
    character(len=*), intent(in) :: routine
    integer :: ierr
    if (rc == -100_c_int) then
       write(*,'(3a)') 'CONQUEST CUDA bridge: device-to-host copy failed in ', routine, &
            '; results are corrupted, aborting.'
       call MPI_Abort(MPI_COMM_WORLD, 1, ierr)
    end if
  end subroutine check_partial_copy

end module cuda_module
