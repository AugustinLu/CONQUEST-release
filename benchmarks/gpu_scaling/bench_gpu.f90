program bench_gpu
  use datatypes
  use cuda_module
  use omp_lib
  implicit none
  integer :: sizes(7) = (/104, 256, 512, 1024, 2048, 3072, 4096/)
  integer :: is, n, info, lwork, lrwork, liwork, m, rep, nrep
  complex(double_cplx), allocatable :: H(:,:), S(:,:), H0(:,:), S0(:,:), Z(:,:), work(:)
  real(double), allocatable :: w_cpu(:), w_gpu(:), rwork(:), rr(:,:), ri(:,:)
  integer, allocatable :: iwork(:), ifail(:)
  real(double) :: t0, t_cpu, t_gpu, t_cpud, maxdiff
  character(len=16) :: arg
  integer :: maxn

  maxn = 4096
  if (command_argument_count() > 0) then
     call get_command_argument(1, arg); read(arg,*) maxn
  end if
  call conquest_cuda_init(0)
  write(*,'(a,l2)') 'CUDA ready: ', flag_cuda_ready

  write(*,'(a)') '--- ZHEGV generalised Hermitian eigenproblem (mode V) ---'
  write(*,'(a)') '     N   zhegvx_CPU(s)  zhegvd_CPU(s)   cuSOLVER(s)   GPUvsX   GPUvsD   max|dE|'
  do is = 1, size(sizes)
     n = sizes(is)
     if (n > maxn) exit
     allocate(H(n,n), S(n,n), H0(n,n), S0(n,n), Z(n,n), w_cpu(n), w_gpu(n), rr(n,n), ri(n,n))
     call random_number(rr); call random_number(ri)
     H0 = cmplx(rr-0.5_double, ri-0.5_double, double_cplx)
     H0 = 0.5_double*(H0 + conjg(transpose(H0)))
     call random_number(rr); call random_number(ri)
     S0 = cmplx(rr-0.5_double, ri-0.5_double, double_cplx) * (0.5_double/n)
     S0 = 0.5_double*(S0 + conjg(transpose(S0)))
     do m = 1, n
        S0(m,m) = S0(m,m) + 1.0_double
     end do
     nrep = 1
     if (n <= 512) nrep = 5
     ! CPU zhegvx (what ScaLAPACK pzhegvx does on one process)
     allocate(work(1), rwork(7*n), iwork(5*n), ifail(n))
     H = H0; S = S0
     call zhegvx(1,'V','A','U',n,H,n,S,n,0.0_double,0.0_double,0,0,0.0_double,m,w_cpu,Z,n,work,-1,rwork,iwork,ifail,info)
     lwork = int(work(1)); deallocate(work); allocate(work(lwork))
     t0 = omp_get_wtime()
     do rep = 1, nrep
        H = H0; S = S0
        call zhegvx(1,'V','A','U',n,H,n,S,n,0.0_double,0.0_double,0,0,0.0_double,m,w_cpu,Z,n,work,lwork,rwork,iwork,ifail,info)
     end do
     t_cpu = (omp_get_wtime()-t0)/nrep
     deallocate(work, rwork, iwork, ifail)
     ! CPU zhegvd
     allocate(work(1), rwork(1), iwork(1))
     H = H0; S = S0
     call zhegvd(1,'V','U',n,H,n,S,n,w_gpu,work,-1,rwork,-1,iwork,-1,info)
     lwork = int(work(1)); lrwork = int(rwork(1)); liwork = iwork(1)
     deallocate(work, rwork, iwork); allocate(work(lwork), rwork(lrwork), iwork(liwork))
     t0 = omp_get_wtime()
     do rep = 1, nrep
        H = H0; S = S0
        call zhegvd(1,'V','U',n,H,n,S,n,w_gpu,work,lwork,rwork,lrwork,iwork,liwork,info)
     end do
     t_cpud = (omp_get_wtime()-t0)/nrep
     deallocate(work, rwork, iwork)
     ! GPU (warm-up first so context/plan creation is not counted)
     H = H0; S = S0
     call conquest_cusolver_zhegv('V', n, H, n, S, n, w_gpu, info)
     t0 = omp_get_wtime()
     do rep = 1, nrep
        H = H0; S = S0
        call conquest_cusolver_zhegv('V', n, H, n, S, n, w_gpu, info)
     end do
     t_gpu = (omp_get_wtime()-t0)/nrep
     maxdiff = maxval(abs(w_cpu - w_gpu))
     write(*,'(i6,3f15.4,2f9.2,es11.2,a,i0)') n, t_cpu, t_cpud, t_gpu, t_cpu/t_gpu, t_cpud/t_gpu, maxdiff, '  info=', info
     deallocate(H, S, H0, S0, Z, w_cpu, w_gpu, rr, ri)
  end do

  call bench_dgemm()
  call conquest_cuda_finalize()

contains

  subroutine bench_dgemm()
    integer, parameter :: ncase = 9
    integer :: ms(ncase) = (/ 13, 13,  64, 200, 200, 500, 1000, 2000, 4000/)
    integer :: ns(ncase) = (/ 13, 300, 64, 200, 200, 500, 1000, 2000, 4000/)
    integer :: ks(ncase) = (/ 13, 13,  64, 64,  200, 500, 1000, 2000, 4000/)
    real(double), allocatable :: A(:,:), B(:,:), C1(:,:), C2(:,:)
    integer :: ic, mm, nn, kk, ierr, nr, r
    real(double) :: tc, tg, fl
    write(*,'(a)') '--- DGEMM C = A^T B (k x m)^T (k x n), incl. PCIe transfers ---'
    write(*,'(a)') '     m     n     k      MFLOP     CPU(ms)     GPU(ms)  GPU speedup   max|dC|'
    do ic = 1, ncase
       mm = ms(ic); nn = ns(ic); kk = ks(ic)
       allocate(A(kk,mm), B(kk,nn), C1(mm,nn), C2(mm,nn))
       call random_number(A); call random_number(B)
       fl = 2.0_double*mm*nn*kk
       nr = max(1, min(2000, int(2.0e10_double/fl)))
       call dgemm('T','N',mm,nn,kk,1.0_double,A,kk,B,kk,0.0_double,C1,mm)
       t0 = omp_get_wtime()
       do r = 1, nr
          call dgemm('T','N',mm,nn,kk,1.0_double,A,kk,B,kk,0.0_double,C1,mm)
       end do
       tc = (omp_get_wtime()-t0)/nr
       cuda_gemm_min_flops = 0
       call conquest_cublas_dgemm('T','N',mm,nn,kk,1.0_double,A,kk,B,kk,0.0_double,C2,mm,ierr)
       t0 = omp_get_wtime()
       do r = 1, nr
          call conquest_cublas_dgemm('T','N',mm,nn,kk,1.0_double,A,kk,B,kk,0.0_double,C2,mm,ierr)
       end do
       tg = (omp_get_wtime()-t0)/nr
       write(*,'(3i6,f11.3,2f12.4,f13.2,es10.2,a,i0)') mm,nn,kk,fl/1e6,tc*1e3,tg*1e3,tc/tg,maxval(abs(C1-C2)),' ierr=',ierr
       deallocate(A,B,C1,C2)
    end do
  end subroutine bench_dgemm
end program bench_gpu
