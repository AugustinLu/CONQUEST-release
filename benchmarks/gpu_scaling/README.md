# CUDA GPU offload: benchmarks and run-time options

CONQUEST built with `src/cuda_bridge.c` + `src/cuda_module.f90` loads the CUDA
libraries (cudart, cuBLAS, cuSOLVER, cuFFT) at run time. No CUDA SDK is needed
to build. Without a GPU or the DLLs, everything runs on the CPU as before.

## Run-time environment variables

| Variable | Default | Meaning |
|---|---|---|
| `CONQUEST_USE_CUDA` | `1` | `0` disables all GPU offload |
| `CONQUEST_CUDA_PATH` | – | directory holding the CUDA libraries, searched first. Then Windows: `%CUDA_PATH%\bin`, `PATH`; Linux: `$CUDA_PATH/lib64`, `$CUDA_HOME/lib64`, `/usr/local/cuda/lib64`, `LD_LIBRARY_PATH`. cuBLAS, cuSOLVER and cuFFT are taken from the same CUDA release (11, 12 or 13) as cudart |
| `CONQUEST_CUDA_DEVICE` | – | GPU index for every process (modulo the number of visible GPUs). By default, the first process of k-point group *g* uses GPU *g*, and other processes use their node-local rank |
| `CONQUEST_CUDA_MIN_N` | `200` | smallest matrix size sent to cuSOLVER `zhegvd` |
| `CONQUEST_CUDA_MIN_FLOPS` | off (`1e30`) | smallest GEMM (in FLOP) sent to cuBLAS; `1e9` is the single-thread break-even, but FP64 cuBLAS never clearly beat 8 CPU cores here |
| `CONQUEST_CUDA_MIN_FFT` | `48` | smallest 3D FFT edge sent to cuFFT (EXX Poisson solver) |
| `CONQUEST_CUDA_IN_PARALLEL` | `0` | `1` also offloads GEMM/FFT calls made from inside OpenMP teams |

The defaults are the break-even points measured on a Quadro RTX 5000 against
a Ryzen 7 5700X (`microbench_results.txt`, produced by `bench_gpu.f90`).

A process creates its CUDA context (and the cuBLAS/cuSOLVER handles) only
when it first offloads something. With the shipped defaults that is only the
first process of each k-point group, so many MPI ranks can share one GPU.
Opt-in GEMM offload, or the EXX cuFFT on every rank, creates one context per
rank (a few hundred MB of GPU memory each); a rank whose context cannot be
created stays on the CPU.

The GPU eigensolver works with any number of MPI ranks. On a 1x1 BLACS grid
(1 rank, or k-point groups of one rank each) it solves in place. On a larger
grid, H and S are gathered onto the first rank of the group (`pzgemr2d`),
solved there, and the eigenvectors are scattered back. Plain MPI is the fastest
setup on Windows, e.g. `mpiexec -n 8 Conquest.exe` with `OMP_NUM_THREADS=1`.
The gathering rank needs room for two extra N x N complex matrices
(2 x 16 N^2 bytes). The legacy cuSOLVER API takes 32-bit sizes, so matrices
with N > 46340 stay on the CPU eigensolver. If the gathered eigensolver fails
once, the run continues with the CPU eigensolver.

At the end of a run, rank 0 prints a usage table: calls, failures and time per
offloaded routine.

## Benchmarks

* `Si*_dzp150/` (64 to 1024 atoms) and `Si*_mssf150/` (256 to 1024 atoms) – the same cells with a DZP basis
  (13 orbitals per atom, generated with MakeIonFiles from `pseudo-and-pao/PBE/Si`, BasisSize medium)
  and a 150 Ha grid, closer to production settings; MSSF contracts DZP to 4 support functions per atom.
  Si1024 stops after 5 SCF iterations.
* `Si256_k222/`, `Si512_k222/` – Si256/Si512 with a 2x2x2 MP mesh and `Diag.KProcGroups 4`, for one GPU per k-point group.
* `Si*_diag/` – bulk Si supercells (64 to 1280 atoms, SZP basis, 9 orbitals/atom,
  Gamma point, 50 Ha grid). `Si1024_diag` and `Si1280_diag` stop after 5 and 3 SCF
  iterations (`SC.MaxIters`, `SC.ContinueOnSCFail T`), so that CPU and GPU do
  the same amount of work.
* `run_gpu_benchmarks.py` – runs the configurations (upstream CPU, patched CPU,
  GPU), keeps each run in `runs/` and appends one JSON line per run to
  `results.jsonl` (Windows) or `runs_<host>/` and `results_<host>.jsonl`
  (Linux/macOS). A configuration is `<upstream|cpu|gpu>_<ranks>x<threads>[_diag]`.
  Examples:
  `python run_gpu_benchmarks.py Si64_diag:all Si512_diag:gpu_1x8,cpu_8x1` (Windows),
  `python3 run_gpu_benchmarks.py Si512_diag:upstream_128x1,cpu_128x1,gpu_128x1,upstream_64x2` (Linux).
  On Linux the patched and upstream executables come from `CONQUEST_EXE` and
  `CONQUEST_REF_EXE`, the launcher from `MPIRUN` (Open MPI core binding is added
  unless `MPIRUN_BIND=0`) and `MPIRUN_OPTS`.
* `measure_mem.py` – runs one case and polls the resident memory of every rank.
* `../../generate_cuda_presentation.py` builds `CONQUEST_CUDA_Acceleration.pptx`
  and the charts from these files.
