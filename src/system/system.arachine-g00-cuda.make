# system.make file for arachine-g00 (NIMS): Ubuntu 20.04, gfortran 9.4, system Open MPI 4.0.3
# Created 2026-10-06 from system.waltz2.make. Standard apt route (no conda).
# apt packages: build-essential openmpi-bin libopenmpi-dev libfftw3-dev libblas-dev liblapack-dev
#               libscalapack-openmpi-dev (all installed on arachine-g00)
# This is the plain apt-route variant (OpenMP on, ELPA off, no MKL), kept under a separate name so that the group's system.arachine-g00.make (Intel MPI + MKL + GPU ELPA) is untouched.
# libxc 6.2.2: STATIC build in $HOME/local (cmake, installed 2026-10-06). The old libxc 4.3.4 (2021) that used to be there was removed (the user asked); a first build with it failed (INTEGER(8)/INTEGER(4) type mismatch in XC_LibXC_v5_module).
# No ELPA in this variant (ELPA_DUMMY = DUMMY). Current develop (2026-09) needs ELPA_DUMMY and -lxcf03.
# Use: make -j8 SYSTEM=arachine-g00-cuda  (reads src/system/system.arachine-g00-cuda.make)
#
# CUDA variant (2026-10-19): identical to system.arachine-g00-apt.make plus the C compiler for
# cuda_bridge.c and -ldl (glibc 2.31 keeps dlopen in libdl). No CUDA SDK is needed to build: the bridge loads
# libcudart/libcublas/libcusolver/libcufft at run time. If they are not in /usr/local/cuda/lib64 or on
# LD_LIBRARY_PATH, set CONQUEST_CUDA_PATH to their directory. CONQUEST_USE_CUDA=0 disables the GPU.
# MULT_KERN stays 'default', as in the upstream reference build (~/local/bin/Conquest-develop); the
# cuBLAS dgemm hook of the multiply kernel is only in ompGemm_m (off by default anyway).

# Set compilers
FC=mpif90
CC=gcc
CFLAGS=-O2

# OpenMP flags
OMPFLAGS= -fopenmp
OMP_DUMMY = 

# Set BLAS and LAPACK libraries
BLAS= -llapack -lblas
# Full scalapack library call (OpenMPI variant)
SCALAPACK = -lscalapack-openmpi

# LibXC compatibility (v5 and v6 have the same interface)
XC_LIBRARY = LibXC_v5
XC_LIB = -lxcf03 -lxc
XC_COMPFLAGS = -I${HOME}/local/include

# Set FFT library
FFT_LIB=-lfftw3
FFT_OBJ=fft_fftw3.o

# Set ELPA library (not used here)
ELPA_LIB =
ELPA_INC =

LIBS= $(FFT_LIB) $(ELPA_LIB) $(XC_LIB) $(SCALAPACK) $(BLAS) -ldl

ARFLAGS=

# Compilation flags (gfortran 9 does NOT know -fallow-argument-mismatch (GCC >= 10 only); rank-mismatch warnings are plain warnings here)
COMPFLAGS= -O3 $(OMPFLAGS) $(XC_COMPFLAGS) $(ELPA_INC) -ffree-line-length-512

# Linking flags
LINKFLAGS= -L${HOME}/local/lib $(OMPFLAGS)

# Matrix multiplication kernel type
MULT_KERN = default
# Use dummy DiagModule or not
DIAG_DUMMY =
# Use dummy ELPAModule or not (required by current develop; ELPA is not used here)
ELPA_DUMMY = DUMMY
