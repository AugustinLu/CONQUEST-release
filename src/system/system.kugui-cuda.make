# system.make file for kugui (ISSP System C) ACC nodes: 4x A100-SXM4-40GB, 64 cores, RHEL 8.10.
# Created 2026-10-20 for the CUDA branch. GNU toolchain instead of the default Cray PE:
#   module unload PrgEnv-cray cray-mpich cray-libsci craype cce perftools-base
#   module load gcc/12.2.0 openmpi_gcc_8.5.0_cuda_12.4/4.1.8 tbb compiler-rt/2024.1.0 mkl/2024.1 cuda/12.4
# (remote/hpc_env.sh does this). BLAS/LAPACK/ScaLAPACK from MKL with the Open MPI BLACS. FFTW 3.3.10 and
# libxc 6.2.2 are built into $(CQ_PREFIX) (remote/build_hpc.sh); FFTW is linked before MKL because MKL's
# FFTW3 wrappers lack the r2r transforms CONQUEST uses. CUDA libraries are loaded at run time from
# /home/app/cuda/12.4 (CUDA_PATH). glibc 2.28: dlopen needs -ldl.
# Use: make -j8 SYSTEM=kugui-cuda

FC=mpif90
CC=gcc
CFLAGS=-O2

OMPFLAGS= -fopenmp
OMP_DUMMY =

BLAS= -L$(MKLROOT)/lib/intel64 -Wl,--no-as-needed -lmkl_gf_lp64 -lmkl_sequential -lmkl_core -lpthread -lm -ldl
SCALAPACK = -lmkl_scalapack_lp64 -lmkl_blacs_openmpi_lp64

XC_LIBRARY = LibXC_v5
XC_LIB = -lxcf03 -lxc
XC_COMPFLAGS = -I$(CQ_PREFIX)/include

FFT_LIB= -L$(CQ_PREFIX)/lib -lfftw3
FFT_OBJ=fft_fftw3.o

ELPA_LIB =
ELPA_INC =

LIBS= $(FFT_LIB) $(ELPA_LIB) $(XC_LIB) $(SCALAPACK) $(BLAS)

ARFLAGS=

COMPFLAGS= -O3 $(OMPFLAGS) $(XC_COMPFLAGS) $(ELPA_INC) -fallow-argument-mismatch -ffree-line-length-512

LINKFLAGS= -L$(CQ_PREFIX)/lib $(OMPFLAGS) -Wl,-rpath,$(MKLROOT)/lib/intel64

MULT_KERN = default
DIAG_DUMMY =
ELPA_DUMMY = DUMMY
