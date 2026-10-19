"""CPU vs CUDA benchmark driver for CONQUEST (Windows/MS-MPI and Linux/macOS).

Runs each Si supercell (diagonalisation, Gamma point) in several configurations,
stores every run in runs[_<host>]/<system>__<config>/ and appends a JSON line per
run to results[_<host>].jsonl (the Windows desktop results are in results.jsonl).

A configuration is <kind>_<ranks>x<threads>[_diag]:
  upstream  unmodified upstream build (CONQUEST_REF_EXE), ScaLAPACK
  cpu       patched build (CONQUEST_EXE) with CONQUEST_USE_CUDA=0
  gpu       patched build with the GPU; with more than one rank, H and S are
            gathered to the first rank of the group for cuSOLVER
  _diag     GEMMs kept on the CPU (CONQUEST_CUDA_MIN_FLOPS=1e18)
"all" runs the configurations used on the Windows desktop (8 cores) or, on
Linux/macOS, upstream/cpu/gpu at BENCH_NP ranks (default: SLURM_NTASKS or the
number of cores).

Usage:  python run_gpu_benchmarks.py Si64_diag:all Si512_diag:gpu_128x1,cpu_128x1,upstream_64x2

Environment (Linux/macOS): CONQUEST_EXE (default ../../bin/Conquest),
CONQUEST_REF_EXE (default ~/local/bin/Conquest-develop), MPIRUN (default mpirun),
MPIRUN_OPTS (extra options; Open MPI binding is added unless MPIRUN_BIND=0),
BENCH_NP. On Windows all runs use below-normal priority so the desktop stays usable.
"""
import json, os, re, shlex, shutil, socket, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
WINDOWS = os.name == "nt"
HOST = socket.gethostname().split(".")[0]

if WINDOWS:
    MSYS_BIN = r"C:\msys64\ucrt64\bin"
    MSMPI_BIN = r"C:\Program Files\Microsoft MPI\Bin"
    MPIEXEC = os.path.join(MSMPI_BIN, "mpiexec.exe")
    EXE_NEW = os.path.join(ROOT, "bin", "Conquest.exe")
    EXE_REF = os.path.abspath(os.path.join(ROOT, "..", "conquest_upstream_ref", "bin", "Conquest.exe"))
    CUDA_DIR = os.environ.get("CONQUEST_CUDA_PATH", r"C:\Users\Khoa\.conda\envs\AtoMROle\Library\bin")
    BELOW_NORMAL = 0x00004000
    RESULTS = os.path.join(HERE, "results.jsonl")
    RUNS = os.path.join(HERE, "runs")
    DEFAULT_ALL = ["upstream_8x1", "cpu_8x1", "cpu_1x8", "gpu_8x1", "gpu_8x1_diag", "gpu_1x8", "gpu_1x1"]
else:
    MPIEXEC = os.environ.get("MPIRUN", "mpirun")
    EXE_NEW = os.environ.get("CONQUEST_EXE", os.path.join(ROOT, "bin", "Conquest"))
    EXE_REF = os.environ.get("CONQUEST_REF_EXE", os.path.expanduser("~/local/bin/Conquest-develop"))
    CUDA_DIR = os.environ.get("CONQUEST_CUDA_PATH", "")
    RESULTS = os.path.join(HERE, f"results_{HOST}.jsonl")
    RUNS = os.path.join(HERE, f"runs_{HOST}")
    NP_DEFAULT = int(os.environ.get("BENCH_NP") or os.environ.get("SLURM_NTASKS") or os.cpu_count())
    DEFAULT_ALL = [f"upstream_{NP_DEFAULT}x1", f"cpu_{NP_DEFAULT}x1", f"gpu_{NP_DEFAULT}x1"]


def config(name):
    """(executable, MPI ranks, OpenMP/BLAS threads, use CUDA, extra environment) for a config name."""
    m = re.fullmatch(r"(upstream|cpu|gpu)_(\d+)x(\d+)(_diag)?", name)
    if not m:
        sys.exit(f"unknown configuration {name!r}: expected <upstream|cpu|gpu>_<ranks>x<threads>[_diag]")
    kind, nproc, nthr, diag = m.group(1), int(m.group(2)), int(m.group(3)), bool(m.group(4))
    exe = EXE_REF if kind == "upstream" else EXE_NEW
    extra = {"CONQUEST_CUDA_MIN_FLOPS": "1e18"} if diag else {}
    return exe, nproc, nthr, kind == "gpu", extra


def launcher(nproc, nthr, exe):
    if WINDOWS:
        return [MPIEXEC, "-priority", "1", "-n", str(nproc), exe]
    cmd = [MPIEXEC]
    if os.environ.get("MPIRUN_BIND", "1") != "0":
        # Open MPI: one core per rank, or nthr consecutive cores per rank
        cmd += ["--map-by", f"slot:PE={nthr}", "--bind-to", "core"] if nthr > 1 else ["--bind-to", "core"]
    cmd += shlex.split(os.environ.get("MPIRUN_OPTS", ""))
    return cmd + ["-np", str(nproc), exe]


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


def parse_gpu_ranks(stdout):
    """Lines like '[CONQUEST CUDA Bridge] rank 0 uses GPU 0 (...)' and the CUDA runtime version."""
    ranks = re.findall(r"rank (\d+) uses GPU (\d+)", stdout)
    rt = re.search(r"CUDA runtime ([0-9.]+)", stdout)
    return {"gpu_ranks": {int(r): int(g) for r, g in ranks}, "cuda_runtime": rt.group(1) if rt else None}


def run(system, cfg):
    exe, nproc, nthr, cuda, extra_env = config(cfg)
    src = os.path.join(HERE, system)
    wd = os.path.join(RUNS, f"{system}__{cfg}")
    if os.path.isdir(wd):
        shutil.rmtree(wd)
    os.makedirs(wd)
    for f in os.listdir(src):
        if os.path.isfile(os.path.join(src, f)):
            shutil.copy(os.path.join(src, f), wd)
    env = os.environ.copy()
    if WINDOWS:
        env["PATH"] = f"{MSYS_BIN};{MSMPI_BIN};{env.get('PATH', '')}"
    env["OMP_NUM_THREADS"] = str(nthr)
    env["OPENBLAS_NUM_THREADS"] = str(nthr)
    env["MKL_NUM_THREADS"] = str(nthr)
    env["OMP_STACKSIZE"] = "100M"
    env["CONQUEST_USE_CUDA"] = "1" if cuda else "0"
    if CUDA_DIR:
        env["CONQUEST_CUDA_PATH"] = CUDA_DIR
    env.update(extra_env)
    cmd = launcher(nproc, nthr, exe)
    t0 = time.perf_counter()
    with open(os.path.join(wd, "stdout.log"), "w") as so:
        p = subprocess.run(cmd, cwd=wd, stdout=so, stderr=subprocess.STDOUT, env=env,
                           **({"creationflags": BELOW_NORMAL} if WINDOWS else {}))
    wall = time.perf_counter() - t0
    out_text = ""
    if os.path.exists(os.path.join(wd, "Conquest_out")):
        out_text = open(os.path.join(wd, "Conquest_out"), errors="ignore").read()
    stdout = open(os.path.join(wd, "stdout.log"), errors="ignore").read()
    rec = {"system": system, "config": cfg, "np": nproc, "nt": nthr, "cuda": cuda,
           "exit_code": p.returncode, "wall_time": wall, "finished": time.strftime("%Y-%m-%d %H:%M:%S")}
    rec.update(parse(out_text or stdout))
    rec["gpu"] = parse_gpu(stdout)
    if not WINDOWS:
        rec.update(host=HOST, exe=exe, command=" ".join(cmd), slurm_job=os.environ.get("SLURM_JOB_ID"))
        rec.update(parse_gpu_ranks(stdout))
    with open(RESULTS, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"{rec['finished']}  {system:<14} {cfg:<13} exit={p.returncode} wall={wall:9.1f}s "
          f"cq={rec['conquest_time']} E={rec['energy']} gpu={rec['gpu']}", flush=True)
    return rec


if __name__ == "__main__":
    for job in sys.argv[1:]:
        system, cfgs = job.split(":")
        cfgs = DEFAULT_ALL if cfgs == "all" else cfgs.split(",")
        for cfg in cfgs:
            run(system, cfg)
