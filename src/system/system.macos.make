# (2026/06/04) system.make file for macOS 26.5.1 with Homebrew
# Apple Silicon (M-Series) Homebrew-Optimized Makefile
# Install packages with : brew install gcc open-mpi scalapack openblas lapack libxc fftw

FC=/opt/homebrew/bin/mpifort

# OpenMP flags
OMPFLAGS= -fopenmp
OMP_DUMMY =

# Set BLAS and LAPACK libraries
BLAS= -llapack -lblas

# Full scalapack library call
SCALAPACK = -lscalapack

# LibXC compatibility
XC_LIBRARY = LibXC_v5
XC_LIB = -lxcf03 -lxc
XC_COMPFLAGS = -I/opt/homebrew/opt/libxc/include

# Set FFT library
FFT_LIB=-lfftw3
FFT_OBJ=fft_fftw3.o

# Set ELPA library (Disabled by default)
ELPA_LIB =
ELPA_INC =
ELPA_DUMMY =DUMMY

LIBS= $(FFT_LIB) $(ELPA_LIB) $(XC_LIB) $(SCALAPACK) $(BLAS)

# Compilation flags
COMPFLAGS= -fallow-argument-mismatch -O3 $(OMPFLAGS) $(XC_COMPFLAGS) $(ELPA_INC) -I/opt/homebrew/opt/openblas/include -I/opt/homebrew/opt/lapack/include -I/opt/homebrew/opt/fftw/include

# Linking flags
LINKFLAGS= $(OMPFLAGS) -L/opt/homebrew/opt/openblas/lib -L/opt/homebrew/opt/lapack/lib -L/opt/homebrew/opt/fftw/lib -L/opt/homebrew/opt/libxc/lib -L/opt/homebrew/opt/scalapack/lib

# Matrix multiplication kernel type
MULT_KERN = default

# Use dummy DiagModule or not
DIAG_DUMMY =