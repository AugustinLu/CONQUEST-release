# CUDA GPU offload: benchmarks and run-time options

CONQUEST built with `src/cuda_bridge.c` + `src/cuda_module.f90` loads the CUDA
libraries (cudart, cuBLAS, cuSOLVER, cuFFT) at run time. No CUDA SDK is needed
to build. Without a GPU or the DLLs, everything runs on the CPU as before.

## Run-time environment variables

| Variable | Default | Meaning |
|---|---|---|
| `CONQUEST_USE_CUDA` | `1` | `0` disables all GPU offload |
| `CONQUEST_CUDA_PATH` | – | directory holding `cudart64_*.dll`, `cublas64_*.dll`, `cusolver64_*.dll`, `cufft64_*.dll` (searched first, then `%CUDA_PATH%\bin`, then `PATH`) |
| `CONQUEST_CUDA_MIN_N` | `200` | smallest matrix size sent to cuSOLVER `zhegvd` |
| `CONQUEST_CUDA_MIN_FLOPS` | off (`1e30`) | smallest GEMM (in FLOP) sent to cuBLAS; `1e9` is the single-thread break-even, but FP64 cuBLAS never clearly beat 8 CPU cores here |
| `CONQUEST_CUDA_MIN_FFT` | `48` | smallest 3D FFT edge sent to cuFFT (EXX Poisson solver) |
| `CONQUEST_CUDA_IN_PARALLEL` | `0` | `1` also offloads GEMM/FFT calls made from inside OpenMP teams |

The defaults are the break-even points measured on a Quadro RTX 5000 against
a Ryzen 7 5700X (`microbench_results.txt`, produced by `bench_gpu.f90`).

The GPU eigensolver works with any number of MPI ranks. On a 1x1 BLACS grid
(1 rank, or k-point groups of one rank each) it solves in place. On a larger
grid, H and S are gathered onto the first rank of the group (`pzgemr2d`),
solved there, and the eigenvectors are scattered back. Plain MPI is the fastest
setup on Windows, e.g. `mpiexec -n 8 Conquest.exe` with `OMP_NUM_THREADS=1`.
The gathering rank needs room for two extra N x N complex matrices
(2 x 16 N^2 bytes).

At the end of a run, rank 0 prints a usage table: calls, failures and time per
offloaded routine.

## Benchmarks

* `Si*_diag/` – bulk Si supercells (64 to 1280 atoms, SZP basis, 9 orbitals/atom,
  Gamma point, 50 Ha grid). `Si1024_diag` and `Si1280_diag` stop after 5 and 3 SCF
  iterations (`SC.MaxIters`, `SC.ContinueOnSCFail T`), so that CPU and GPU do
  the same amount of work.
* `run_gpu_benchmarks.py` – runs the configurations (upstream CPU, patched CPU,
  GPU), keeps each run in `runs/` and appends one JSON line per run to
  `results.jsonl`. Example:
  `python run_gpu_benchmarks.py Si64_diag:all Si512_diag:gpu_1x8,cpu_8x1`
* `../../generate_cuda_presentation.py` builds `CONQUEST_CUDA_Acceleration.pptx`
  and the charts from these files.
