#!/usr/bin/env python3
"""Create CONQUEST run directories for finite-difference Born effective charges.

Each atom (or a chosen subset) is displaced by +delta and -delta along the
Cartesian x, y and z axes, one coordinate at a time, from a reference
calculation directory.  The cell may be general (non-orthogonal): with
fractional coordinates, the Cartesian step is converted with the inverse
lattice, so it may change several fractional coordinates.
Every run directory receives a copy of the reference Conquest_input (with
``Process.Job pol`` and ``Process.BerryDirection 0`` set so that
PostProcessCQ writes the Berry-phase data for all three directions), the
displaced coordinates and the files listed with --copy (the *.ion files of
REF by default).  The coordinates are written to the base name of
IO.Coordinates inside each run directory; IO.Coordinates is set to that
name and any Process.Coordinates is removed, so that CONQUEST and
PostProcessCQ both read the displaced structure.  A Conquest_input for the
final ``Process.Job bec`` step is written to the output directory, with
the Process.PolarisationRuns block listing the reference first.  Keywords
are replaced with CONQUEST's label matching (case and the characters
``.``, ``_``, ``-`` ignored): every earlier occurrence is removed.

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
import math
import os
import re
import shutil
import sys

BOHR_TO_ANG = 0.52917721067  # as CONQUEST units.module.f90


def strip_comment(line):
    """Remove a trailing CONQUEST comment (!, # or ;)."""
    return re.split(r"[!#;]", line, maxsplit=1)[0]


def norm_label(label):
    """CONQUEST label matching: case and the characters . _ - are ignored."""
    return re.sub(r"[._-]", "", label).lower()


def read_keywords(path):
    """Keyword -> value (first occurrence, CONQUEST label matching); block contents skipped."""
    keys = {}
    in_block = False
    with open(path) as fh:
        for raw in fh:
            line = strip_comment(raw).strip()
            if not line:
                continue
            low = line.lower()
            if low.startswith("%block"):
                in_block = True
                continue
            if low.startswith("%endblock"):
                in_block = False
                continue
            if in_block or line.startswith("%"):
                continue
            parts = line.split(None, 1)
            keys.setdefault(norm_label(parts[0]), parts[1].strip() if len(parts) > 1 else "T")
    return keys


def get(keys, name, default=None):
    return keys.get(norm_label(name), default)


def is_true(value):
    return value is not None and value.strip().lower() in ("t", "true", ".true.", "y", "yes")


def read_coords(path):
    """Lattice vectors (rows a_1, a_2, a_3) and atom lines of a CONQUEST coordinate file."""
    with open(path) as fh:
        lines = [l for l in fh if l.strip()]
    cell = [[float(v) for v in lines[i].split()[:3]] for i in range(3)]
    nat = int(lines[3].split()[0])
    atoms = []
    for l in lines[4:4 + nat]:
        p = l.split()
        atoms.append([float(p[0]), float(p[1]), float(p[2])] + p[3:])
    return cell, atoms


def is_diagonal(cell):
    return all(cell[i][j] == 0.0 for i in range(3) for j in range(3) if i != j)


def inverse3(m):
    """Inverse of a 3x3 matrix (list of rows)."""
    det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
           - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
           + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    if abs(det) < 1e-12:
        sys.exit("Singular lattice in the coordinate file")
    return [[(m[(j + 1) % 3][(i + 1) % 3] * m[(j + 2) % 3][(i + 2) % 3]
              - m[(j + 1) % 3][(i + 2) % 3] * m[(j + 2) % 3][(i + 1) % 3]) / det
             for j in range(3)] for i in range(3)]


def write_coords(path, cell, atoms):
    with open(path, "w") as fh:
        for row in cell:
            fh.write(" ".join(f"{v:.12f}" for v in row) + "\n")
        fh.write(f"{len(atoms)}\n")
        for a in atoms:
            fh.write(f"{a[0]:.12f} {a[1]:.12f} {a[2]:.12f} " + " ".join(a[3:]) + "\n")


def set_keys(text, keys, blocks=()):
    """Return Conquest_input text with every occurrence of the keywords in
    ``keys`` (name -> value, or None to delete) and of the blocks in
    ``blocks`` (name -> list of lines, or None to delete) removed, and the
    new values appended once at the end (CONQUEST uses the first occurrence)."""
    want = {norm_label(k): (k, v) for k, v in keys.items()}
    want_blocks = {norm_label(k): (k, v) for k, v in dict(blocks).items()}
    out = []
    skipping = False
    in_block = False
    for raw in text.splitlines():
        line = strip_comment(raw).strip()
        low = line.lower()
        if low.startswith("%block"):
            name = line.split()[1] if len(line.split()) > 1 else ""
            in_block = True
            skipping = norm_label(name) in want_blocks
            if skipping:
                continue
        elif low.startswith("%endblock"):
            in_block = False
            if skipping:
                skipping = False
                continue
        elif skipping:
            continue
        elif line and not in_block and norm_label(line.split()[0]) in want:
            continue
        out.append(raw)
    new = [f"{k} {v}" for k, v in want.values() if v is not None]
    for k, v in want_blocks.values():
        if v is not None:
            new += [f"%block {k}"] + list(v) + [f"%endblock {k}"]
    text = "\n".join(out).rstrip("\n") + "\n"
    if new:
        text += "\n# Set by make_bec_displacements.py\n" + "\n".join(new) + "\n"
    return text


def set_process_job(text, job, extra=""):
    """Return Conquest_input text with Process.Job set to ``job`` (all earlier
    occurrences under any CONQUEST spelling removed)."""
    return set_keys(text, {"Process.Job": job}) + extra


def parse_atoms(spec, nat):
    """'1,2,5-8' -> sorted list of 1-based atom indices; exits on errors."""
    sel = set()
    for part in spec.split(","):
        part = part.strip()
        try:
            if "-" in part:
                lo, hi = (int(v) for v in part.split("-"))
                if lo > hi:
                    sys.exit(f"Reversed atom range '{part}'")
                sel.update(range(lo, hi + 1))
            else:
                sel.add(int(part))
        except ValueError:
            sys.exit(f"Cannot read atom selection '{part}' (use e.g. '1,2,5-8')")
    if not sel:
        sys.exit("Empty atom selection")
    if any(i < 1 or i > nat for i in sel):
        sys.exit(f"Atom index out of range 1-{nat}")
    return sorted(sel)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ref", help="reference calculation directory (Conquest_input, coordinates, ions)")
    ap.add_argument("out", help="output directory to create")
    ap.add_argument("--delta", type=float, default=0.02, help="displacement in bohr (default 0.02)")
    ap.add_argument("--atoms", type=str, default="",
                    help="atoms to displace, 1-based, e.g. '1,2,5-8' (default all)")
    ap.add_argument("--one-sided", action="store_true", help="only +delta (forward differences)")
    ap.add_argument("--copy", nargs="*", default=None,
                    help="files to copy from REF into every directory (default: the *.ion files of REF)")
    args = ap.parse_args()

    if not (math.isfinite(args.delta) and args.delta > 0):
        sys.exit("--delta must be a positive number (bohr)")
    inp = os.path.join(args.ref, "Conquest_input")
    keys = read_keywords(inp)
    coord_path = get(keys, "IO.Coordinates")
    if coord_path is None:
        sys.exit("IO.Coordinates not found in " + inp)
    coord_path = coord_path.split()[0]
    proc_coords = get(keys, "Process.Coordinates")
    if proc_coords is not None and proc_coords.split()[0] != coord_path:
        print(f"Note: Process.Coordinates {proc_coords.split()[0]} in REF is removed; PostProcessCQ "
              "will read the displaced IO.Coordinates file")
    if is_true(get(keys, "IO.PdbIn", "F")):
        sys.exit("PDB coordinate input (IO.PdbIn T) is not supported; use a CONQUEST coordinate file")
    frac = is_true(get(keys, "IO.FractionalAtomicCoords", "T"))
    units = (get(keys, "General.DistanceUnits", "bohr") or "bohr").lower()
    to_file = 1.0  # bohr -> file distance units
    if units.startswith("a") and not units.startswith("a0"):
        to_file = BOHR_TO_ANG  # file distances in Angstrom
    cell, atoms = read_coords(os.path.join(args.ref, coord_path))
    # Fractional change for a Cartesian step along axis b: rows a_j of the
    # cell give r = sum_j f_j a_j, so df_j = step * (cell^-1)[b][j]
    if is_diagonal(cell):
        if any(not (cell[i][i] > 0) for i in range(3)):
            sys.exit("Cell lengths must be positive")
        frac_step = [[(1.0 / cell[b][b] if j == b else 0.0) for j in range(3)] for b in range(3)]
    else:
        frac_step = inverse3(cell)
    berry_dir = get(keys, "Process.BerryDirection")
    if berry_dir is not None and berry_dir.split()[0] != "0":
        print(f"Note: Process.BerryDirection {berry_dir.split()[0]} in REF is replaced by 0 "
              "(BEC needs all three directions)")

    selection = parse_atoms(args.atoms, len(atoms)) if args.atoms else list(range(1, len(atoms) + 1))

    # Files written by this script, in every directory
    coord_name = os.path.basename(coord_path)
    generated = {coord_name, "Conquest_input"}
    if coord_name in ("", "Conquest_input"):
        sys.exit(f"Unusable coordinate file name '{coord_path}'")
    copies = args.copy
    if copies is None:
        copies = sorted(f for f in os.listdir(args.ref) if f.endswith(".ion"))
    seen = set()
    for f in copies:
        base = os.path.basename(f)
        if base in generated:
            sys.exit(f"--copy {f} would overwrite the generated {base}")
        if base in seen:
            sys.exit(f"--copy lists two files named {base}")
        seen.add(base)
        if not os.path.isfile(os.path.join(args.ref, f)):
            sys.exit(f"--copy: {os.path.join(args.ref, f)} not found")
    text = open(inp).read()
    common = {"IO.Coordinates": coord_name, "Process.Coordinates": None}
    run_text = set_keys(text, dict(common, **{"Process.Job": "pol", "Process.BerryDirection": "0"}))

    os.makedirs(args.out, exist_ok=False)
    runs = []

    def make_run(name, new_atoms):
        d = os.path.join(args.out, name)
        os.makedirs(d)
        for f in copies:  # dependencies first, generated files last
            shutil.copy2(os.path.join(args.ref, f), os.path.join(d, os.path.basename(f)))
        write_coords(os.path.join(d, coord_name), cell, new_atoms)
        with open(os.path.join(d, "Conquest_input"), "w") as fh:
            fh.write(run_text)
        runs.append(name)

    def check_step(name, i, b, s):
        """The displaced file must differ from the reference by s*delta bohr along b for atom i only."""
        _, ref_atoms = read_coords(os.path.join(args.out, "ref", coord_name))
        _, new_atoms = read_coords(os.path.join(args.out, name, coord_name))
        for j, (p, q) in enumerate(zip(ref_atoms, new_atoms)):
            df = [q[c] - p[c] for c in range(3)]
            if frac:  # fractional change -> Cartesian, r = sum_k f_k a_k (rows a_k of cell)
                df = [sum(df[k] * cell[k][c] for k in range(3)) for c in range(3)]
            for c in range(3):
                d = df[c] / to_file
                expect = s * args.delta if (j == i - 1 and c == b) else 0.0
                if abs(d - expect) > 1e-8 * max(1.0, args.delta):
                    sys.exit(f"Internal check failed for {name}: atom {j + 1} coordinate {c + 1} "
                             f"moved by {d} bohr, expected {expect}")

    make_run("ref", [list(a) for a in atoms])
    signs = [(+1, "p")] if args.one_sided else [(+1, "p"), (-1, "m")]
    for i in selection:
        for b, axis in enumerate("xyz"):
            for s, tag in signs:
                new = [list(a) for a in atoms]
                step = s * args.delta * to_file  # in file distance units
                if frac:
                    if is_diagonal(cell):
                        new[i - 1][b] += step / cell[b][b]
                    else:
                        for j in range(3):
                            new[i - 1][j] += step * frac_step[b][j]
                else:
                    new[i - 1][b] += step
                name = f"a{i:04d}_{axis}_{tag}"
                make_run(name, new)
                check_step(name, i, b, s)

    for f in copies:
        shutil.copy2(os.path.join(args.ref, f), os.path.join(args.out, os.path.basename(f)))
    write_coords(os.path.join(args.out, coord_name), cell, atoms)
    bec_text = set_keys(text, dict(common, **{"Process.Job": "bec"}),
                        {"Process.PolarisationRuns": runs})
    with open(os.path.join(args.out, "Conquest_input"), "w") as fh:
        fh.write(bec_text)
    print(f"Created {len(runs)} run directories in {args.out} (delta = {args.delta} bohr);")
    print("run Conquest and PostProcessCQ in each, then PostProcessCQ in " + args.out)


if __name__ == "__main__":
    main()
