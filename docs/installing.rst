.. _install:

============
Installation
============

You will need to download and compile the code before you can use it;
we do not supply binaries.

.. _install_down:

Downloading
-----------

CONQUEST is accessed from `the GitHub repository
<https://github.com/OrderN/CONQUEST-release/>`_;
it can be cloned:

``git clone https://github.com/OrderN/CONQUEST-release destination-directory``

where ``destination-directory`` should be set by the user.
Alternatively, it can be downloaded from GitHub as a zip file and
unpacked: 

`<https://github.com/OrderN/CONQUEST-release/archive/master.zip>`_

.. _install_compile:

Compiling
---------

Once you have the distribution, you will need to compile the main
Conquest code (found in the ``src/`` directory), along with the ion file
generation code (found in the ``tools/`` directory).  Conquest requires
a working MPI installation including a Fortran90 compiler (often
``mpif90`` but this can vary), along with a few standard libraries:

* BLAS and LAPACK (normally provided by the system vendor)
* FFTW 3.x (more detail can be found at `http://www.fftw.org/ <http://www.fftw.org/>`_)
* ScaLAPACK (often provided as part of an HPC system; the source code
  can be obtained from `the netlib repository <http://www.netlib.org/scalapack/>`_ if
  you need to compile it)

Additionally, Conquest can use LibXC if it is available (v2.x or
later).

The library locations are set in the ``system.<systemname>.make`` file in the ``src/system``
directory, along with other parameters needed for compilation. ``system.<systemname>.make``
files are provided for some HPC systems used by the community, but if you want to run
locally or on a different system, you need to provide an appropriate ``system.<systemname>.make``
file. Use ``src/system/system.example.make`` as a starting point. Get the ``<systemname>``
by running ``hostname -d`` in your prompt, then name your file appropriately and move it to
the ``src/system`` directory. If ``hostname -d`` returns empty (e.g. you are running on a
local machine), the system-specific makefile should be named ``system.make``.

* ``FC`` (typically ``FC=mpif90`` will be all that is required)
* ``COMPFLAGS`` (set these to specify compiler options such as
  optimisation)
* ``BLAS`` (specify the BLAS and LAPACK libraries)
* ``SCALAPACK`` (specify the ScaLAPACK library)
* ``FFT_LIB`` (must be left as FFTW)
* ``XC_LIBRARY`` (choose ``XC_LIBRARY=CQ`` for the internal Conquest
  library, otherwise ``XC_LIBRARY=LibXC_v2or3`` for LibXC v2.x or v3.x, or ``XC_LIBRARY=LibXC_v4``
  for LibXC v4.x)
* Two further options need to be set for LibXC:

  + ``XC_LIB`` (specify the XC libraries)
  + ``XC_COMPFLAGS`` (specify the location of the LibXC include and
    module files, e.g. ``-I/usr/local/include``)

Once these are set, you should make the executable using ``make``.

The ion file generation code is compiled using the same options
required for the main code.

Multi-threading
~~~~~~~~~~~~~~~

CONQUEST can use OpenMP for multi-threading; some multi-threading is available throughout the code, while there are specific matrix multiplication routines which can use multi-threading for the linear scaling solver.  The number of threads is set via the environment variable ``OMP_NUM_THREADS``.

Compiler flags to enable OpenMP are dependent on the vendor, but should be specified via ``COMPFLAGS`` and ``LINKFLAGS`` in the ``system.make`` file.  If compiling with OpenMP then you should also change the variable ``OMP_DUMMY`` in the same file to be blank to enable the number of threads to be included in the output.

On some systems, the default stack size for OpenMP is set to be rather small, and this can cause a segmentation fault when running with multiple threads.  We recommend testing the effect of the environment variable ``OMP_STACKSIZE`` (and suggest setting it to 50M or larger as a first test).


Compilation on Ubuntu
~~~~~~~~~~~~~~~
Most of the required packages are available on Ubuntu's Advanced Packaging Tool (APT) and can be installed via the below commands.
This installation method has been confirmed for standalone Ubuntu 22.04 as well as the Windows Subsystem for Linux (WSL).

```bash
# Install needed packages
sudo apt update
sudo apt upgrade

sudo apt install -y build-essential # gcc and other tools for software development

sudo apt install -y openmpi-bin libopenmpi-dev # MPI
sudo apt install -y libfftw3-dev # FFT
sudo apt install -y libblas-dev liblapack-dev libscalapack-openmpi-dev # Linear algebra
```

For libXC, separate compilation is needed:

```bash
# Install libxc
cd $HOME && mkdir local
cd $HOME/local && mkdir src && cd src

cd $HOME/local/src
wget http://www.tddft.org/programs/libxc/down.php?file=6.2.2/libxc-6.2.2.tar.gz -O libxc.tar.gz
tar -zxf libxc.tar.gz
cd libxc-6.2.2 && ./configure --prefix=$HOME/local
make -j4
make check && make install
```


```bash
# Download CONQUEST
cd $HOME/local/src
git clone https://github.com/OrderN/CONQUEST-release.git conquest_master
cd conquest_master/src
```

```bash
# Prepare system.make file for Ubuntu. For develop branch, use system/system.make
cat > system.make << EOF
#

# Set compilers
FC=mpif90
F77=mpif77

# Linking flags
LINKFLAGS= -L\${HOME}/local/lib -L/usr/local/lib -fopenmp
ARFLAGS=

# Compilation flags
# NB for gcc10 you need to add -fallow-argument-mismatch
COMPFLAGS= -O3 \$(XC_COMPFLAGS) -fallow-argument-mismatch
COMPFLAGS_F77= \$(COMPFLAGS)

# Set BLAS and LAPACK libraries
# MacOS X
# BLAS= -lvecLibFort
# Intel MKL use the Intel tool
# Generic
BLAS= -llapack -lblas

# Full library call; remove scalapack if using dummy diag module
LIBS= \$(FFT_LIB) \$(XC_LIB) -lscalapack-openmpi \$(BLAS)

# LibXC compatibility (LibXC below) or Conquest XC library

# Conquest XC library
#XC_LIBRARY = CQ
#XC_LIB =
#XC_COMPFLAGS =

# LibXC compatibility
# Choose LibXC version: v4 (deprecated) or v5/6 (v5 and v6 have the same interface)
# XC_LIBRARY = LibXC_v4
XC_LIBRARY = LibXC_v5
XC_LIB = -lxcf90 -lxc
#XC_COMPFLAGS = -I/usr/local/include
XC_COMPFLAGS = -I\${HOME}/local/include -I/usr/local/include

# Set FFT library
FFT_LIB=-lfftw3
FFT_OBJ=fft_fftw3.o

# Matrix multiplication kernel type
MULT_KERN = default
# Use dummy DiagModule or not
DIAG_DUMMY =

EOF
```

```
# Compile
dos2unix ./makedeps # Some windows/unix incompatibilities may occur
make -j4 # Or make -j`nproc`  # Uses all cores available
```