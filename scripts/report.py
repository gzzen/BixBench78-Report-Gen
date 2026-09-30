"""Write report/<run_name>/results.csv and summary.json for a RunEval."""
import csv
import json
import statistics as st
from collections import defaultdict
from datetime import datetime, timezone

from .config import REPORT_DIR

CSV_COLUMNS = [
    "question_id", "capsule", "eval_mode", "status", "correctness", "answer", "ideal",
    "time_sec", "tokens_total", "question_content", "llm_evaluation",
    "categories", "check_note", "tokens_input", "tokens_output", "tokens_reasoning",
    "tokens_cache_read", "cost", "steps", "error",
]


def _acc(rows):
    n = len(rows)
    correct = sum(1 for r in rows if r["correctness"] is True)
    unscored = sum(1 for r in rows if r["correctness"] is None)
    return {"n": n, "correct": correct, "unscored": unscored,
            "accuracy": round(correct / n, 4) if n else None}


def _group(rows, keyfn):
    groups = defaultdict(list)
    for r in rows:
        groups[keyfn(r)].append(r)
    return {k: _acc(v) for k, v in sorted(groups.items(), key=lambda kv: str(kv[0]))}


def _dist(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return {"n": len(vals), "total": round(sum(vals), 2), "mean": round(st.mean(vals), 2),
            "median": round(st.median(vals), 2), "min": min(vals), "max": max(vals)}


def summarize(ev):
    rows = ev.records
    answered = [r for r in rows if r["answer"] is not None]
    overall = _acc(rows)
    answered_acc = _acc(answered)
    return {
        "run_name": ev.run_name,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "judge_model": ev.judge_model,
        "n_questions": overall["n"],
        "n_correct": overall["correct"],
        "n_unscored": overall["unscored"],
        "accuracy": overall["accuracy"],                      # correct / all questions
        "n_answered": answered_acc["n"],
        "accuracy_answered": answered_acc["accuracy"],        # correct / questions with an answer
        "status_counts": dict(sorted(_count(r["status"] for r in rows).items())),
        "by_eval_mode": _group(rows, lambda r: r["eval_mode"]),
        "by_capsule": _group(rows, lambda r: r["capsule"]),
        "by_category": _group(rows, lambda r: r["categories"] or "unknown"),
        "time_sec": _dist([r["time_sec"] for r in rows]),
        "tokens_total": _dist([r["tokens_total"] for r in rows]),
        "tokens_output": _dist([r["tokens_output"] for r in rows]),
        "cost": _dist([r["cost"] for r in rows]),
    }


def _count(it):
    out = defaultdict(int)
    for x in it:
        out[x] += 1
    return out


def write_report(ev, out_root=REPORT_DIR):
    out = out_root / ev.run_name
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "results.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in ev.records:
            row = dict(r)
            if row["correctness"] is None:
                row["correctness"] = ""
            w.writerow(row)
    summary = summarize(ev)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out, summary
