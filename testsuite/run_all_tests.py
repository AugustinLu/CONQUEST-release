#!/usr/bin/env python3
"""Run every numbered CONQUEST test and write JSON and PDF reports.

MPI launches are intercepted so that every CONQUEST invocation uses no more
than one rank per three atoms, with a configurable global rank ceiling.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TESTSUITE = ROOT / "testsuite"
DEFAULT_PDF = ROOT / "output" / "pdf" / "conquest_all_tests_report.pdf"
TEST_PATTERN = re.compile(r"test_(\d{3})_")
COORDINATE_PATTERN = re.compile(
    r"^\s*IO\.Coordinates\s*(?:=|:)??\s+([^\s#;]+)", re.IGNORECASE
)


def uncommented_lines(path: Path) -> list[str]:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return []
    lines = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def coordinate_atom_count(path: Path) -> int | None:
    """Read CONQUEST's three-vectors, atom-count, coordinates format."""
    lines = uncommented_lines(path)
    if len(lines) < 4:
        return None
    try:
        for line in lines[:3]:
            values = line.split()
            if len(values) < 3:
                return None
            tuple(float(value) for value in values[:3])
        token = lines[3].split()[0]
        count = int(token)
    except (ValueError, IndexError):
        return None
    return count if count > 0 else None


def referenced_coordinate_names(path: Path) -> set[str]:
    names: set[str] = set()
    for line in uncommented_lines(path):
        match = COORDINATE_PATTERN.match(line)
        if match:
            names.add(Path(match.group(1).strip("'\"")).name)
    return names


def discover_atom_counts(test_dir: Path) -> list[int]:
    """Discover source coordinate sets without inspecting old result trees."""
    source_files = [
        path
        for path in test_dir.iterdir()
        if path.is_file()
        and not path.name.startswith("Conquest_out")
        and path.suffix.lower() not in {".ion", ".gto", ".png", ".pdf"}
    ]
    names: set[str] = set()
    for path in source_files:
        names.update(referenced_coordinate_names(path))

    candidates = [path for path in source_files if path.name in names]
    if not candidates:
        candidates = source_files

    counts = {
        count
        for path in candidates
        if (count := coordinate_atom_count(path)) is not None
    }
    return sorted(counts)


def rank_limit(atom_count: int | None, maximum: int) -> int:
    if atom_count is None:
        return 1
    return max(1, min(maximum, atom_count // 3))


def canonical_entrypoint(test_dir: Path, number: int) -> tuple[str, list[str]]:
    if number <= 9:
        return "direct CONQUEST run + pytest reference comparison", []
    candidates = [
        "run_workflow.sh",
        "run_exact_mic.sh",
        "run_block_distance.sh",
        "run_surface_geometry.sh",
    ]
    for name in candidates:
        path = test_dir / name
        if path.is_file():
            return name, ["bash", str(path)]
    return "no canonical entrypoint", []


def workflow_rank_ceiling(command: list[str], default: int) -> int:
    """Return a workflow's explicit NP ceiling when it declares one."""
    if len(command) < 2:
        return default
    try:
        source = Path(command[1]).read_text(errors="replace")
    except OSError:
        return default
    upper_bounds = [
        int(value)
        for value in re.findall(r"(?:\$\{?NP\}?|NP)\s*(?:>|-gt)\s*[\"']?(\d+)", source)
    ]
    allowed_values = [
        int(value)
        for value in re.findall(r"(?:\$\{?NP\}?|NP)[\"']?\s*!=\s*[\"']?(\d+)", source)
    ]
    declared = upper_bounds + ([max(allowed_values)] if allowed_values else [])
    return min(default, min(declared)) if declared else default


MPI_GUARD = r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import re
import sys
import time

COORD_RE = re.compile(r"^\s*IO\.Coordinates\s*(?:=|:)??\s+([^\s#;]+)", re.I)

def content_lines(path):
    try:
        rows = path.read_text(errors="replace").splitlines()
    except OSError:
        return []
    return [row.split("#", 1)[0].strip() for row in rows
            if row.split("#", 1)[0].strip()]

def count_from_coords(path):
    rows = content_lines(path)
    if len(rows) < 4:
        return None
    try:
        for row in rows[:3]:
            tuple(float(value) for value in row.split()[:3])
        value = int(rows[3].split()[0])
        return value if value > 0 else None
    except (ValueError, IndexError):
        return None

def current_atom_count():
    input_path = Path.cwd() / "Conquest_input"
    for row in content_lines(input_path):
        match = COORD_RE.match(row)
        if match:
            value = count_from_coords(Path.cwd() / match.group(1).strip("'\""))
            if value:
                return value
    for name in ("coords.dat", "coord.dat", "Conquest_coord"):
        value = count_from_coords(Path.cwd() / name)
        if value:
            return value
    try:
        fallback = int(os.environ.get("CONQUEST_ATOM_FALLBACK", ""))
        return fallback if fallback > 0 else None
    except ValueError:
        return None

args = sys.argv[1:]
requested = None
rank_index = None
for index, value in enumerate(args[:-1]):
    if value in ("-np", "-n", "--np"):
        try:
            requested = int(args[index + 1])
            rank_index = index + 1
        except ValueError:
            pass
        break

atoms = current_atom_count()
maximum = int(os.environ.get("CONQUEST_MPI_MAX", "3"))
allowed = 1 if atoms is None else max(1, min(maximum, atoms // 3))
used = min(requested, allowed) if requested is not None else allowed
if rank_index is not None:
    args[rank_index] = str(used)

record = {
    "time": time.time(),
    "cwd": str(Path.cwd()),
    "atoms": atoms,
    "requested": requested,
    "allowed": allowed,
    "used": used,
    "command": args,
}
log_path = os.environ.get("CONQUEST_MPI_GUARD_LOG")
if log_path:
    with open(log_path, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")

real_mpi = os.environ["CONQUEST_REAL_MPI_LAUNCHER"]
os.execvpe(real_mpi, [real_mpi, *args], os.environ)
'''


def make_mpi_guard(run_root: Path, real_mpi: str) -> Path:
    guard_dir = run_root / "mpi_guard_bin"
    guard_dir.mkdir(parents=True, exist_ok=True)
    guard = guard_dir / "mpirun"
    guard.write_text(MPI_GUARD)
    guard.chmod(0o755)
    mpiexec = guard_dir / "mpiexec"
    if not mpiexec.exists():
        mpiexec.symlink_to(guard.name)
    return guard


def run_logged(
    command: list[str], cwd: Path, env: dict[str, str], log_path: Path
) -> tuple[int, float]:
    start = time.monotonic()
    with log_path.open("w", encoding="utf-8", errors="replace") as stream:
        stream.write(f"cwd: {cwd}\ncommand: {shlex.join(command)}\n\n")
        stream.flush()
        process = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return process.returncode, time.monotonic() - start


def extract_highlights(paths: list[Path], limit: int = 8) -> list[str]:
    patterns = (
        "passed",
        "failed",
        "error",
        "converged",
        "tolerance",
        "maximum absolute",
        "rms",
        "invariance",
        "success",
    )
    found: list[str] = []
    for path in paths:
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            clean = " ".join(line.split())
            if clean and any(word in clean.lower() for word in patterns):
                found.append(clean[:220])
    deduplicated = list(dict.fromkeys(found))
    return deduplicated[-limit:]


def read_guard_records(path: Path, test_name: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if test_name in record.get("cwd", ""):
            records.append(record)
    return records


def git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def pdf_report(summary: dict[str, Any], destination: Path) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            BaseDocTemplate,
            Frame,
            KeepTogether,
            PageBreak,
            PageTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise RuntimeError(
            "PDF generation requires reportlab; run with /opt/anaconda3/bin/python"
        ) from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    width, height = A4
    navy = colors.HexColor("#17324D")
    pale = colors.HexColor("#EAF2F8")
    green = colors.HexColor("#1B7F5A")
    red = colors.HexColor("#B33A3A")
    amber = colors.HexColor("#A66A00")
    grey = colors.HexColor("#5E6A73")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=25, leading=30, textColor=navy, alignment=TA_CENTER,
        spaceAfter=8 * mm,
    ))
    styles.add(ParagraphStyle(
        name="Deck", parent=styles["Normal"], fontSize=11, leading=16,
        textColor=grey, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="Section", parent=styles["Heading1"], fontSize=16, leading=20,
        textColor=navy, spaceBefore=5 * mm, spaceAfter=3 * mm,
    ))
    styles.add(ParagraphStyle(
        name="Test", parent=styles["Heading2"], fontSize=11, leading=14,
        textColor=navy, spaceAfter=1.5 * mm,
    ))
    styles.add(ParagraphStyle(
        name="Small", parent=styles["Normal"], fontSize=7.8, leading=10,
        textColor=colors.HexColor("#263238"),
    ))
    styles.add(ParagraphStyle(
        name="Tiny", parent=styles["Normal"], fontName="Courier", fontSize=6.5,
        leading=8.2, textColor=grey,
    ))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D8E0E7"))
        canvas.line(18 * mm, 13 * mm, width - 18 * mm, 13 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(grey)
        canvas.drawString(18 * mm, 8.5 * mm, "CONQUEST complete test-suite report")
        canvas.drawRightString(width - 18 * mm, 8.5 * mm, f"Page {doc.page}")
        canvas.restoreState()

    frame = Frame(18 * mm, 17 * mm, width - 36 * mm, height - 33 * mm,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    document = BaseDocTemplate(
        str(destination), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=17 * mm,
        title="CONQUEST complete test-suite report",
        author="CONQUEST validation runner",
    )
    document.addPageTemplates(PageTemplate(id="main", frames=[frame], onPage=footer))

    tests = summary["tests"]
    passed = sum(item["status"] == "PASS" for item in tests)
    failed = sum(item["status"] == "FAIL" for item in tests)
    skipped = len(tests) - passed - failed
    story = [
        Spacer(1, 34 * mm),
        Paragraph("CONQUEST complete test-suite report", styles["CoverTitle"]),
        Paragraph(
            f"Branch {summary['git']['branch']}<br/>Commit {summary['git']['commit']}<br/>"
            f"Run completed {summary['finished_at']}", styles["Deck"]
        ),
        Spacer(1, 16 * mm),
    ]
    cards = Table([
        [Paragraph(f"<b>{passed}</b><br/>passed", styles["Deck"]),
         Paragraph(f"<b>{failed}</b><br/>failed", styles["Deck"]),
         Paragraph(f"<b>{skipped}</b><br/>not run", styles["Deck"])],
    ], colWidths=[54 * mm] * 3, rowHeights=[28 * mm])
    cards.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#E7F5EF")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FBECEC")),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#FFF4DB")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5DC")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.extend([cards, Spacer(1, 13 * mm)])
    story.append(Paragraph(
        "MPI policy: every launch was capped at max(1, min(3, floor(number of atoms / 3))). "
        "OpenMP was fixed at one thread and the build used no more than three jobs.",
        styles["Deck"],
    ))
    story.append(PageBreak())

    story.append(Paragraph("Results overview", styles["Section"]))
    overview = [["Test", "Atoms", "MPI ranks used", "Time", "Status"]]
    for item in tests:
        ranks = ", ".join(str(value) for value in item["mpi_ranks_used"]) or "none"
        overview.append([
            item["name"], str(item["atom_count"] or "n/a"), ranks,
            f"{item['duration_seconds']:.1f} s", item["status"],
        ])
    table = Table(overview, repeatRows=1,
                  colWidths=[82 * mm, 17 * mm, 31 * mm, 22 * mm, 20 * mm])
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), navy),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("LEADING", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5DC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, pale]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for row, item in enumerate(tests, start=1):
        status_color = green if item["status"] == "PASS" else red if item["status"] == "FAIL" else amber
        commands.append(("TEXTCOLOR", (-1, row), (-1, row), status_color))
        commands.append(("FONTNAME", (-1, row), (-1, row), "Helvetica-Bold"))
    table.setStyle(TableStyle(commands))
    story.extend([table, PageBreak(), Paragraph("Test-by-test detail", styles["Section"])])

    for item in tests:
        status_color = green if item["status"] == "PASS" else red if item["status"] == "FAIL" else amber
        ranks = ", ".join(str(value) for value in item["mpi_ranks_used"]) or "none"
        meta = Table([
            ["Status", Paragraph(f"<b><font color='{status_color.hexval()}'>{item['status']}</font></b>", styles["Small"]),
             "Duration", f"{item['duration_seconds']:.2f} s"],
            ["Atoms", str(item["atom_count"] or "not applicable"), "MPI ranks", ranks],
            ["Entrypoint", Paragraph(item["entrypoint"], styles["Small"]), "Exit code", str(item["exit_code"])],
        ], colWidths=[19 * mm, 68 * mm, 22 * mm, 48 * mm])
        meta.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), pale),
            ("BACKGROUND", (2, 0), (2, -1), pale),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5DC")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        details = [Paragraph(item["name"], styles["Test"]), meta]
        if item["highlights"]:
            details.append(Spacer(1, 1.5 * mm))
            details.append(Paragraph("Validation highlights", styles["Small"]))
            for line in item["highlights"]:
                escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                details.append(Paragraph(f"- {escaped}", styles["Tiny"]))
        details.extend([
            Paragraph(f"Log: {item['log']}", styles["Tiny"]),
            Spacer(1, 5 * mm),
        ])
        story.append(KeepTogether(details))

    story.append(PageBreak())
    story.append(Paragraph("Provenance and method", styles["Section"]))
    provenance = [
        ["Repository", summary["git"]["root"]],
        ["Branch", summary["git"]["branch"]],
        ["Commit", summary["git"]["commit"]],
        ["Upstream Test 005 fix", "a8fcebb6 - Initialize eri_gto to zero"],
        ["Build", summary["build"]["status"] + f" ({summary['build']['duration_seconds']:.1f} s)"],
        ["Host", summary["host"]],
        ["Python", summary["python"]],
    ]
    provenance_table = Table(provenance, colWidths=[42 * mm, 123 * mm])
    provenance_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), pale),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5DC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([provenance_table, Spacer(1, 5 * mm)])
    story.append(Paragraph(
        "A PASS means the numbered test's canonical workflow returned zero and, for tests 001-009, "
        "the matching pytest reference comparisons also passed against a freshly written Conquest_out. "
        "The MPI guard re-read each active Conquest_input and coordinate file at launch time, so generated "
        "multi-stage workflows were constrained using their actual atom counts wherever available.",
        styles["Small"],
    ))
    document.build(story)


def parse_selection(values: list[str] | None) -> set[int] | None:
    if not values:
        return None
    selected: set[int] = set()
    for value in values:
        for part in value.split(","):
            if "-" in part:
                start, end = (int(item) for item in part.split("-", 1))
                selected.update(range(start, end + 1))
            else:
                selected.add(int(part))
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-mpi", type=int, default=3,
                        help="global MPI-rank ceiling (default: 3)")
    parser.add_argument("--build-jobs", type=int, default=3,
                        help="parallel build jobs, capped at 3 (default: 3)")
    parser.add_argument("--tests", action="append",
                        help="test numbers or ranges, e.g. 1-9,12,28")
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--no-pdf", action="store_true")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--run-root", type=Path,
                        help="result directory (default: testsuite/test_runs/TIMESTAMP)")
    args = parser.parse_args()
    if args.max_mpi < 1:
        parser.error("--max-mpi must be positive")
    args.max_mpi = min(args.max_mpi, 3)
    args.build_jobs = max(1, min(args.build_jobs, 3))
    selection = parse_selection(args.tests)

    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    run_root = (args.run_root or TESTSUITE / "test_runs" / stamp).resolve()
    log_dir = run_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    mpi_log = run_root / "mpi_invocations.jsonl"
    real_mpi = shutil.which("mpirun")
    if not real_mpi:
        raise SystemExit("mpirun was not found")
    guard = make_mpi_guard(run_root, real_mpi)

    base_env = os.environ.copy()
    base_env.update({
        "OMP_NUM_THREADS": "1",
        "OMP_STACKSIZE": "100M",
        "CONQUEST_MPI_MAX": str(args.max_mpi),
        "CONQUEST_MPI_GUARD_LOG": str(mpi_log),
        "CONQUEST_REAL_MPI_LAUNCHER": real_mpi,
        "MPI_LAUNCHER": str(guard),
        "BACKGROUND_MODE": "F",
        "CONQUEST_BIN": str(ROOT / "bin" / "Conquest"),
        "PYTHON": "/opt/anaconda3/bin/python" if Path("/opt/anaconda3/bin/python").is_file() else sys.executable,
        "PATH": str(guard.parent) + os.pathsep + base_env.get("PATH", ""),
        "TMPDIR": str(run_root / "tmp"),
    })
    Path(base_env["TMPDIR"]).mkdir(parents=True, exist_ok=True)

    started = dt.datetime.now().astimezone()
    build_log = log_dir / "build.log"
    if args.no_build:
        build_code, build_duration = 0, 0.0
        build_status = "SKIPPED"
    else:
        build_code, build_duration = run_logged(
            ["make", f"-j{args.build_jobs}"], ROOT / "src", base_env, build_log
        )
        build_status = "PASS" if build_code == 0 else "FAIL"
    print(f"Build: {build_status} ({build_duration:.1f} s)", flush=True)

    test_dirs = []
    for path in sorted(TESTSUITE.glob("test_[0-9][0-9][0-9]_*")):
        match = TEST_PATTERN.match(path.name)
        if match and (selection is None or int(match.group(1)) in selection):
            test_dirs.append((int(match.group(1)), path))

    records: list[dict[str, Any]] = []
    for number, test_dir in test_dirs:
        name = test_dir.name
        counts = discover_atom_counts(test_dir)
        atom_count = min(counts) if counts else None
        entrypoint, command = canonical_entrypoint(test_dir, number)
        workflow_max = workflow_rank_ceiling(command, args.max_mpi)
        ranks = min(rank_limit(atom_count, args.max_mpi), workflow_max)
        log_path = log_dir / f"{name}.log"
        env = base_env.copy()
        env["NP"] = str(ranks)
        env["MPI_RANKS"] = str(ranks)
        if atom_count:
            env["CONQUEST_ATOM_FALLBACK"] = str(atom_count)

        if build_code != 0:
            code, duration, status = 125, 0.0, "NOT RUN"
            log_path.write_text("Not run because the build failed.\n")
        elif number <= 9:
            output_path = test_dir / "Conquest_out"
            old_mtime = output_path.stat().st_mtime_ns if output_path.exists() else -1
            code, duration = run_logged(
                [str(guard), "-np", str(ranks), str(ROOT / "bin" / "Conquest")],
                test_dir, env, log_path,
            )
            fresh_output = output_path.exists() and output_path.stat().st_mtime_ns > old_mtime
            if code == 0 and fresh_output:
                pytest_command = [
                    env["PYTHON"], "-m", "pytest", "-q",
                    str(TESTSUITE / "test_check_output.py"), "-k", f"test_{number:03d}",
                ]
                with log_path.open("a", encoding="utf-8") as stream:
                    stream.write("\nreference validation: " + shlex.join(pytest_command) + "\n\n")
                    pytest_start = time.monotonic()
                    pytest_result = subprocess.run(
                        pytest_command, cwd=TESTSUITE, env=env,
                        stdout=stream, stderr=subprocess.STDOUT, check=False,
                    )
                    duration += time.monotonic() - pytest_start
                code = pytest_result.returncode
            elif code == 0:
                code = 124
                with log_path.open("a", encoding="utf-8") as stream:
                    stream.write("ERROR: Conquest_out was not freshly written; reference check suppressed.\n")
            status = "PASS" if code == 0 else "FAIL"
        elif not command:
            code, duration, status = 127, 0.0, "NOT RUN"
            log_path.write_text("No canonical test entrypoint found.\n")
        else:
            code, duration = run_logged(command, test_dir, env, log_path)
            status = "PASS" if code == 0 else "FAIL"

        guard_records = read_guard_records(mpi_log, name)
        ranks_used = sorted({int(item["used"]) for item in guard_records})
        highlights = extract_highlights(
            [log_path, test_dir / "Conquest_out"], limit=8
        )
        record = {
            "number": number,
            "name": name,
            "status": status,
            "exit_code": code,
            "duration_seconds": round(duration, 3),
            "atom_count": atom_count,
            "discovered_atom_counts": counts,
            "rank_cap": ranks,
            "workflow_rank_cap": workflow_max,
            "mpi_ranks_used": ranks_used,
            "mpi_invocations": len(guard_records),
            "entrypoint": entrypoint,
            "log": str(log_path),
            "highlights": highlights,
        }
        records.append(record)
        print(f"{name}: {status} | atoms={atom_count or 'n/a'} | ranks={ranks_used or 'none'} | {duration:.1f} s", flush=True)

    finished = dt.datetime.now().astimezone()
    summary = {
        "schema_version": 1,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": finished.isoformat(timespec="seconds"),
        "duration_seconds": round((finished - started).total_seconds(), 3),
        "git": {
            "root": str(ROOT),
            "branch": git_value("branch", "--show-current"),
            "commit": git_value("rev-parse", "--short=12", "HEAD"),
            "describe": git_value("describe", "--tags", "--always", "--dirty"),
        },
        "host": os.uname().nodename,
        "python": sys.version.split()[0],
        "mpi_policy": "max(1, min(3, floor(atom_count / 3)))",
        "build": {
            "status": build_status,
            "exit_code": build_code,
            "duration_seconds": round(build_duration, 3),
            "jobs": args.build_jobs,
            "log": str(build_log),
        },
        "tests": records,
    }
    summary_path = run_root / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"Summary: {summary_path}")
    if not args.no_pdf:
        pdf_report(summary, args.pdf.resolve())
        print(f"PDF: {args.pdf.resolve()}")
    return 0 if build_code == 0 and all(item["status"] == "PASS" for item in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
