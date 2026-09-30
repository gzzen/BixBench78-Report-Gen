"""Paths and small helpers shared by the evaluator."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
RUN_OUTPUT_DIR = ROOT / "run_output"
REPORT_DIR = ROOT / "report"
CACHE_DIR = ROOT / ".cache"
ANSWERS_PATH = SRC_DIR / "answers_78.json"
QUESTIONS_PATH = SRC_DIR / "questions_78.json"


def load_dotenv(path=ROOT / ".env"):
    """Minimal .env reader (KEY=VALUE lines); real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
