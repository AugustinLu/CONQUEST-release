"""CPU vs CUDA benchmark driver for the CONQUEST Windows build.

Runs each Si supercell (diagonalisation, Gamma point) in several configurations,
stores every run in runs/<system>__<config>/ and appends a JSON line per run to
results.jsonl. All runs use below-normal priority so the desktop stays usable.

Usage:  python run_gpu_benchmarks.py Si64_diag:cpu_8x1,gpu_1x8 Si256_diag:all ...
"""
import json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MSYS_BIN = r"C:\msys64\ucrt64\bin"
MSMPI_BIN = r"C:\Program Files\Microsoft MPI\Bin"
MPIEXEC = os.path.join(MSMPI_BIN, "mpiexec.exe")
EXE_NEW = os.path.join(ROOT, "bin", "Conquest.exe")
EXE_REF = os.path.abspath(os.path.join(ROOT, "..", "conquest_upstream_ref", "bin", "Conquest.exe"))
CUDA_DLL_DIR = os.environ.get("CONQUEST_CUDA_PATH", r"C:\Users\Khoa\.conda\envs\AtoMROle\Library\bin")
BELOW_NORMAL = 0x00004000

# name: (executable, MPI ranks, OpenMP/BLAS threads, use CUDA, extra environment)
CONFIGS = {
    "upstream_8x1": (EXE_REF, 8, 1, False, {}),   # unmodified upstream code, ScaLAPACK on 8 ranks
    "cpu_8x1":      (EXE_NEW, 8, 1, False, {}),   # patched code, CUDA disabled, 8 ranks
    "cpu_1x8":      (EXE_NEW, 1, 8, False, {}),   # patched code, CUDA disabled, 1 rank x 8 threads
    "gpu_8x1":      (EXE_NEW, 8, 1, True, {}),    # 8 ranks, H/S gathered to rank 0 for cuSOLVER
    "gpu_8x1_diag": (EXE_NEW, 8, 1, True, {"CONQUEST_CUDA_MIN_FLOPS": "1e18"}),  # as above, GEMMs kept on CPU
    "gpu_1x8":      (EXE_NEW, 1, 8, True, {}),    # 1 rank x 8 threads, local cuSOLVER
    "gpu_1x1":      (EXE_NEW, 1, 1, True, {}),    # 1 rank x 1 thread
}


def parse(out_text):
    r = {}
    m = re.search(r"Total run time was:\s+([0-9.]+)\s+seconds", out_text)
    r["conquest_time"] = float(m.group(1)) if m else None
    m = re.findall(r"Harris-Foulkes energy\s+=\s+([-0-9.]+)", out_text)
    r["energy"] = float(m[-1]) if m else None
    m = re.search(r"Max total mem use is\s+([0-9.]+)\s+MB", out_text)
    r["memory_mb"] = float(m.group(1)) if m else None
    r["scf_iterations"] = len(re.findall(r"SCF iteration|Residual is ", out_text)) or None
    return r


def parse_gpu(stdout):
    stats = {}
    for line in stdout.splitlines():
        m = re.match(r"\s+(cuSOLVER zhegvd|cuBLAS dgemm|cuBLAS zgemm|cuFFT 3D z2z)\s+(\d+)\s+(\d+)\s+([0-9.]+)", line)
        if m:
            stats[m.group(1)] = {"calls": int(m.group(2)), "failed": int(m.group(3)), "time": float(m.group(4))}
    return stats


def run(system, cfg):
    exe, nproc, nthr, cuda, extra_env = CONFIGS[cfg]
    src = os.path.join(HERE, system)
    wd = os.path.join(HERE, "runs", f"{system}__{cfg}")
    if os.path.isdir(wd):
        shutil.rmtree(wd)
    os.makedirs(wd)
    for f in os.listdir(src):
        if os.path.isfile(os.path.join(src, f)):
            shutil.copy(os.path.join(src, f), wd)
    env = os.environ.copy()
    env["PATH"] = f"{MSYS_BIN};{MSMPI_BIN};{env.get('PATH', '')}"
    env["OMP_NUM_THREADS"] = str(nthr)
    env["OPENBLAS_NUM_THREADS"] = str(nthr)
    env["OMP_STACKSIZE"] = "100M"
    env["CONQUEST_USE_CUDA"] = "1" if cuda else "0"
    env["CONQUEST_CUDA_PATH"] = CUDA_DLL_DIR
    env.update(extra_env)
    cmd = [MPIEXEC, "-priority", "1", "-n", str(nproc), exe]
    t0 = time.perf_counter()
    with open(os.path.join(wd, "stdout.log"), "w") as so:
        p = subprocess.run(cmd, cwd=wd, stdout=so, stderr=subprocess.STDOUT, env=env,
                           creationflags=BELOW_NORMAL)
    wall = time.perf_counter() - t0
    out_text = ""
    if os.path.exists(os.path.join(wd, "Conquest_out")):
        out_text = open(os.path.join(wd, "Conquest_out"), errors="ignore").read()
    stdout = open(os.path.join(wd, "stdout.log"), errors="ignore").read()
    rec = {"system": system, "config": cfg, "np": nproc, "nt": nthr, "cuda": cuda,
           "exit_code": p.returncode, "wall_time": wall, "finished": time.strftime("%Y-%m-%d %H:%M:%S")}
    rec.update(parse(out_text or stdout))
    rec["gpu"] = parse_gpu(stdout)
    with open(os.path.join(HERE, "results.jsonl"), "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"{rec['finished']}  {system:<14} {cfg:<13} exit={p.returncode} wall={wall:9.1f}s "
          f"cq={rec['conquest_time']} E={rec['energy']} gpu={rec['gpu']}", flush=True)
    return rec


if __name__ == "__main__":
    for job in sys.argv[1:]:
        system, cfgs = job.split(":")
        cfgs = list(CONFIGS) if cfgs == "all" else cfgs.split(",")
        for cfg in cfgs:
            run(system, cfg)
