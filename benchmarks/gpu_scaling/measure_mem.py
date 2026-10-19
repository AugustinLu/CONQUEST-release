"""Run one CONQUEST case and record peak memory (per rank and summed) by polling.

Usage: python measure_mem.py <input dir> <work dir> <MPI ranks> <use CUDA 0|1>

Every process whose name starts with the executable's name is sampled once per
second (psutil RSS), so short runs can be missed. Uses the same executable and
launcher settings as run_gpu_benchmarks.py (CONQUEST_EXE, MPIRUN, MPIRUN_OPTS
on Linux/macOS; MS-MPI on Windows).
"""
import os, re, shutil, subprocess, sys, time
import psutil

from run_gpu_benchmarks import WINDOWS, EXE_NEW, CUDA_DIR, launcher

src, wd, nproc, cuda = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4] == "1"
if os.path.isdir(wd):
    shutil.rmtree(wd)
shutil.copytree(src, wd)
env = os.environ.copy()
if WINDOWS:
    from run_gpu_benchmarks import MSYS_BIN, MSMPI_BIN
    env["PATH"] = f"{MSYS_BIN};{MSMPI_BIN};{env['PATH']}"
env.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", OMP_STACKSIZE="100M",
           CONQUEST_USE_CUDA="1" if cuda else "0")
if CUDA_DIR:
    env["CONQUEST_CUDA_PATH"] = CUDA_DIR
exe_name = os.path.basename(EXE_NEW)
t0 = time.time()
p = subprocess.Popen(launcher(nproc, 1, EXE_NEW),
                     cwd=wd, stdout=open(os.path.join(wd, "stdout.log"), "w"), stderr=subprocess.STDOUT, env=env)
peak_rank, peak_sum, min_free = {}, 0, 1e18
while p.poll() is None:
    tot = 0
    for q in psutil.process_iter(["name", "pid"]):
        if (q.info["name"] or "").startswith(exe_name[:15]):   # Linux truncates names to 15 characters
            try:
                rss = q.memory_info().rss
            except psutil.Error:
                continue
            peak_rank[q.pid] = max(peak_rank.get(q.pid, 0), rss)
            tot += rss
    peak_sum = max(peak_sum, tot)
    min_free = min(min_free, psutil.virtual_memory().available)
    time.sleep(1.0)
out = open(os.path.join(wd, "Conquest_out"), errors="ignore").read() if os.path.exists(os.path.join(wd, "Conquest_out")) else ""
t = re.search(r"Total run time was:\s+([0-9.]+)", out)
e = re.findall(r"Harris-Foulkes energy\s+=\s+([-0-9.]+)", out)
ranks = sorted(peak_rank.values(), reverse=True)
print(f"{os.path.basename(wd)}: exit={p.returncode} time={t.group(1) if t else None}s E={e[-1] if e else None} "
      f"sum_peak={peak_sum/2**30:.2f}GB rank_peaks_GB={[round(r/2**30, 2) for r in ranks]} "
      f"min_free_RAM={min_free/2**30:.1f}GB wall={time.time()-t0:.0f}s", flush=True)
