"""Run one CONQUEST case and record peak memory (per rank and summed) by polling."""
import os, re, shutil, subprocess, sys, time
import psutil

MSYS_BIN = r"C:\msys64\ucrt64\bin"
MSMPI_BIN = r"C:\Program Files\Microsoft MPI\Bin"
EXE = r"D:\Documents\Projects\CONQUEST\conquest_for_windows\bin\Conquest.exe"
CUDA_DIR = r"C:\Users\Khoa\.conda\envs\AtoMROle\Library\bin"

src, wd, nproc, cuda = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4] == "1"
if os.path.isdir(wd):
    shutil.rmtree(wd)
shutil.copytree(src, wd)
env = os.environ.copy()
env["PATH"] = f"{MSYS_BIN};{MSMPI_BIN};{env['PATH']}"
env.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", OMP_STACKSIZE="100M",
           CONQUEST_USE_CUDA="1" if cuda else "0", CONQUEST_CUDA_PATH=CUDA_DIR)
t0 = time.time()
p = subprocess.Popen([os.path.join(MSMPI_BIN, "mpiexec.exe"), "-priority", "1", "-n", str(nproc), EXE],
                     cwd=wd, stdout=open(os.path.join(wd, "stdout.log"), "w"), stderr=subprocess.STDOUT, env=env)
peak_rank, peak_sum, min_free = {}, 0, 1e18
while p.poll() is None:
    tot = 0
    for q in psutil.process_iter(["name", "pid"]):
        if q.info["name"] == "Conquest.exe":
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
