# system.make file for Wisteria/BDEC-01 Aquarius nodes (U. Tokyo): 8x A100-SXM4-40GB, 2x Xeon Ice Lake, RHEL 8.10.
# Created 2026-10-20 for the CUDA branch. GNU toolchain:
#   module load aquarius cuda/12.2 gcc/8.3.1 ompi-cuda/4.1.5-12.2 fftw/3.3.9
#   MKLROOT=/work/opt/local/x86_64/cores/intel/2023.1.0/mkl/latest (MKL used with gfortran)
# (remote/hpc_env.sh does this). BLAS/LAPACK/ScaLAPACK from MKL with the Open MPI BLACS; FFTW from the
# fftw/3.3.9 module, libxc 6.2.2 built into $(CQ_PREFIX) (remote/build_hpc.sh); FFTW is linked before MKL because MKL's
# FFTW3 wrappers lack the r2r transforms CONQUEST uses. CUDA libraries are loaded at run time from
# $(CUDA_PATH)/lib64 (cuda/12.2 module). gfortran 8: no -fallow-argument-mismatch. glibc 2.28: -ldl.
# Use: make -j8 SYSTEM=wisteria-aquarius-cuda

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

FFT_LIB= -L$(FFTW_DIR)/lib -lfftw3
FFT_OBJ=fft_fftw3.o

ELPA_LIB =
ELPA_INC =

LIBS= $(FFT_LIB) $(ELPA_LIB) $(XC_LIB) $(SCALAPACK) $(BLAS)

ARFLAGS=

COMPFLAGS= -O3 $(OMPFLAGS) $(XC_COMPFLAGS) $(ELPA_INC) -ffree-line-length-512

LINKFLAGS= -L$(CQ_PREFIX)/lib $(OMPFLAGS) -Wl,-rpath,$(MKLROOT)/lib/intel64 -Wl,-rpath,$(FFTW_DIR)/lib

MULT_KERN = default
DIAG_DUMMY =
ELPA_DUMMY = DUMMY
