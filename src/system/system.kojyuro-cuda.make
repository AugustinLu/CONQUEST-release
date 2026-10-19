# system.make file for kojyuro (WSLab, UTokyo): Ubuntu 24.04, gfortran 13, system Open MPI 4.1.6
# Created 2026-10-06 from system.waltz2.make. Standard apt route (no conda).
# apt packages: build-essential openmpi-bin libopenmpi-dev libfftw3-dev libblas-dev liblapack-dev
#               libscalapack-openmpi-dev (all installed on kojyuro)
# libxc 6.2.2 is the existing STATIC build in $HOME/local (lib/libxc.a, libxcf03.a; include/*.mod); the rpath below is then unused.
# No ELPA in this variant (ELPA_DUMMY = DUMMY). Current develop (2026-09) needs ELPA_DUMMY and -lxcf03.
# Use: make -j8 SYSTEM=kojyuro-cuda  (reads src/system/system.kojyuro-cuda.make)
#
# CUDA variant (2026-10-19): identical to system.kojyuro.make plus the C compiler for cuda_bridge.c.
# kojyuro has a TITAN V (Volta) and driver 550 (CUDA <= 12.4); /usr/local/cuda points to CUDA 13.0,
# which neither the driver nor Volta supports. The bridge skips it and finds /usr/local/cuda-12.6
# (CUDA 12 minor-version compatibility); CONQUEST_CUDA_PATH=/usr/local/cuda-12.6/lib64 forces it.

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

LIBS= $(FFT_LIB) $(ELPA_LIB) $(XC_LIB) $(SCALAPACK) $(BLAS)

ARFLAGS=

# Compilation flags (gcc >= 10 needs -fallow-argument-mismatch)
COMPFLAGS= -O3 $(OMPFLAGS) $(XC_COMPFLAGS) $(ELPA_INC) -fallow-argument-mismatch -ffree-line-length-512

# Linking flags
LINKFLAGS= -L${HOME}/local/lib $(OMPFLAGS) -Wl,-rpath,${HOME}/local/lib

# Matrix multiplication kernel type
MULT_KERN = default
# Use dummy DiagModule or not
DIAG_DUMMY =
# Use dummy ELPAModule or not (required by current develop; ELPA is not used here)
ELPA_DUMMY = DUMMY
