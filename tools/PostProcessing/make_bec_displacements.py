#!/usr/bin/env python3
"""Create CONQUEST run directories for finite-difference Born effective charges.

Each atom (or a chosen subset) is displaced by +delta and -delta along x, y
and z, one coordinate at a time, from a reference calculation directory.
Every run directory receives a copy of the reference Conquest_input (with
``Process.Job pol`` set so that PostProcessCQ writes the Berry-phase data
file), the displaced coordinates and the files listed with --copy (ion
files by default).  A Conquest_input for the final ``Process.Job bec`` step
is written to the output directory, with the Process.PolarisationRuns block
listing the reference first.

Workflow:
    make_bec_displacements.py REF OUT --delta 0.02
    for d in OUT/ref OUT/a*; do (cd $d; mpirun Conquest; PostProcessCQ); done
    cd OUT && PostProcessCQ          # Process.Job bec

The reference Conquest_input must already be set up for the Berry phase:
static diagonalisation, Diag.MPMesh, and IO.outputWF with IO.maxnoWF and a
WaveFunctionsOut block covering all occupied bands.

Only the Python standard library is used.
"""
import argparse
import os
import re
import shutil
import sys

BOHR_TO_ANG = 0.52917721067  # as CONQUEST units.module.f90


def strip_comment(line):
    """Remove a trailing CONQUEST comment (!, # or ;)."""
    return re.split(r"[!#;]", line, maxsplit=1)[0]


def read_keywords(path):
    """Keyword -> value (first occurrence, CONQUEST label matching)."""
    keys = {}
    with open(path) as fh:
        for raw in fh:
            line = strip_comment(raw).strip()
            if not line or line.startswith("%"):
                continue
            parts = line.split(None, 1)
            label = re.sub(r"[._-]", "", parts[0]).lower()
            keys.setdefault(label, parts[1].strip() if len(parts) > 1 else "T")
    return keys


def get(keys, name, default=None):
    return keys.get(re.sub(r"[._-]", "", name).lower(), default)


def is_true(value):
    return value is not None and value.strip().lower() in ("t", "true", ".true.", "y", "yes")


def read_coords(path):
    with open(path) as fh:
        lines = [l for l in fh if l.strip()]
    cell = [[float(v) for v in lines[i].split()[:3]] for i in range(3)]
    for i in range(3):
        for j in range(3):
            if i != j and abs(cell[i][j]) > 1e-10:
                sys.exit("Only orthorhombic cells are supported (off-diagonal lattice vector component)")
    nat = int(lines[3].split()[0])
    atoms = []
    for l in lines[4:4 + nat]:
        p = l.split()
        atoms.append([float(p[0]), float(p[1]), float(p[2])] + p[3:])
    return cell, atoms


def write_coords(path, cell, atoms):
    with open(path, "w") as fh:
        for row in cell:
            fh.write(" ".join(f"{v:.12f}" for v in row) + "\n")
        fh.write(f"{len(atoms)}\n")
        for a in atoms:
            fh.write(f"{a[0]:.12f} {a[1]:.12f} {a[2]:.12f} " + " ".join(a[3:]) + "\n")


def set_process_job(text, job, extra=""):
    """Return Conquest_input text with Process.Job replaced or appended."""
    pat = re.compile(r"^\s*process[._-]?job\b.*$", re.IGNORECASE | re.MULTILINE)
    if pat.search(text):
        text = pat.sub(f"Process.Job {job}", text, count=1)
    else:
        text = text.rstrip("\n") + f"\n\n# PostProcessCQ\nProcess.Job {job}\n"
    return text + extra


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ref", help="reference calculation directory (Conquest_input, coordinates, ions)")
    ap.add_argument("out", help="output directory to create")
    ap.add_argument("--delta", type=float, default=0.02, help="displacement in bohr (default 0.02)")
    ap.add_argument("--atoms", type=str, default="",
                    help="atoms to displace, 1-based, e.g. '1,2,5-8' (default all)")
    ap.add_argument("--one-sided", action="store_true", help="only +delta (forward differences)")
    ap.add_argument("--copy", nargs="*", default=None,
                    help="files to copy from REF (default: *.ion and any block file)")
    args = ap.parse_args()

    inp = os.path.join(args.ref, "Conquest_input")
    keys = read_keywords(inp)
    coord_name = get(keys, "IO.Coordinates")
    if coord_name is None:
        sys.exit("IO.Coordinates not found in " + inp)
    coord_name = coord_name.split()[0]
    if is_true(get(keys, "IO.PdbIn", "F")):
        sys.exit("PDB coordinate input (IO.PdbIn T) is not supported; use a CONQUEST coordinate file")
    frac = is_true(get(keys, "IO.FractionalAtomicCoords", "T"))
    units = (get(keys, "General.DistanceUnits", "bohr") or "bohr").lower()
    to_file = 1.0  # bohr -> file distance units
    if units.startswith("a") and not units.startswith("a0"):
        to_file = BOHR_TO_ANG  # file distances in Angstrom
    cell, atoms = read_coords(os.path.join(args.ref, coord_name))
    lengths = [cell[i][i] for i in range(3)]  # in file units

    if args.atoms:
        sel = set()
        for part in args.atoms.split(","):
            if "-" in part:
                lo, hi = part.split("-")
                sel.update(range(int(lo), int(hi) + 1))
            else:
                sel.add(int(part))
        selection = sorted(sel)
    else:
        selection = list(range(1, len(atoms) + 1))
    if any(i < 1 or i > len(atoms) for i in selection):
        sys.exit("Atom index out of range")

    copies = args.copy
    if copies is None:
        copies = [f for f in os.listdir(args.ref) if f.endswith(".ion")]
    text = open(inp).read()
    run_text = set_process_job(text, "pol")

    os.makedirs(args.out, exist_ok=False)
    runs = []

    def make_run(name, new_atoms):
        d = os.path.join(args.out, name)
        os.makedirs(d)
        write_coords(os.path.join(d, coord_name), cell, new_atoms)
        with open(os.path.join(d, "Conquest_input"), "w") as fh:
            fh.write(run_text)
        for f in copies:
            shutil.copy2(os.path.join(args.ref, f), d)
        runs.append(name)

    make_run("ref", [list(a) for a in atoms])
    signs = [(+1, "p")] if args.one_sided else [(+1, "p"), (-1, "m")]
    for i in selection:
        for b, axis in enumerate("xyz"):
            for s, tag in signs:
                new = [list(a) for a in atoms]
                step = s * args.delta * to_file  # in file distance units
                if frac:
                    new[i - 1][b] += step / lengths[b]
                else:
                    new[i - 1][b] += step
                make_run(f"a{i:04d}_{axis}_{tag}", new)

    block = "%block Process.PolarisationRuns\n" + "\n".join(runs) + "\n%endblock Process.PolarisationRuns\n"
    bec_text = set_process_job(text, "bec", "\n" + block)
    with open(os.path.join(args.out, "Conquest_input"), "w") as fh:
        fh.write(bec_text)
    write_coords(os.path.join(args.out, coord_name), cell, atoms)
    for f in copies:
        shutil.copy2(os.path.join(args.ref, f), args.out)
    print(f"Created {len(runs)} run directories in {args.out} (delta = {args.delta} bohr);")
    print("run Conquest and PostProcessCQ in each, then PostProcessCQ in " + args.out)


if __name__ == "__main__":
    main()
