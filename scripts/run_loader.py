"""Read one run directory (run_output/<name>/, same layout as the baseline export)."""
import json
import re
from pathlib import Path

from .config import RUN_OUTPUT_DIR


def resolve_run_dir(name):
    """Accept a run name (looked up in run_output/) or an explicit path."""
    p = Path(name)
    if p.is_dir():
        return p.resolve()
    p = RUN_OUTPUT_DIR / name
    if p.is_dir():
        return p
    raise FileNotFoundError(f"run not found: {name!r} (looked in {RUN_OUTPUT_DIR})")


def load_results(run_dir):
    """question_id -> {status, answer, error}. Falls back to per-worker results."""
    top = run_dir / "results" / "all_results.json"
    if top.exists():
        rows = json.loads(top.read_text(encoding="utf-8"))
    else:
        rows = []
        for f in sorted((run_dir / "workers").glob("q*/results/all_results.json")):
            rows.extend(json.loads(f.read_text(encoding="utf-8")))
    return {r["question_id"]: r for r in rows}


def worker_dirs(run_dir):
    """question_id -> worker directory (dir names look like q001_bix_10_q1)."""
    out = {}
    for wd in (run_dir / "workers").glob("q*"):
        m = re.match(r"^q\d+_(bix)_(\d+)_q(\d+)$", wd.name)
        if m:
            out[f"{m.group(1)}-{m.group(2)}-q{m.group(3)}"] = wd
    return out
