"""Evaluate one run against the answer key. Pure function of (run dir, answer key, questions);
returns a RunEval so reports - and later, cross-run comparisons - can be built from the records."""
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from .config import ANSWERS_PATH, QUESTIONS_PATH
from .log_metrics import parse_worker_log
from .run_loader import load_results, resolve_run_dir, worker_dirs
from .verifiers import verify_range, verify_str


@dataclass
class RunEval:
    run_name: str
    run_dir: str
    records: list                      # one dict per question, in answer-key order
    judge_model: str | None = None
    meta: dict = field(default_factory=dict)


def load_answer_key():
    return json.loads(ANSWERS_PATH.read_text(encoding="utf-8"))


def load_questions():
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def _row(qid, key, qmeta, res, metrics):
    return {
        "question_id": qid,
        "capsule": qmeta.get("capsule") or qid.rsplit("-q", 1)[0],
        "eval_mode": key["eval_mode"],
        "status": res.get("status", "missing"),
        "correctness": None,
        "answer": res.get("answer"),
        "ideal": key["ideal"],
        "time_sec": metrics["time_sec"],
        "tokens_total": metrics["tokens_total"],
        "question_content": qmeta.get("question", ""),
        "llm_evaluation": "",
        # extras (not required, useful for analysis / comparison)
        "categories": qmeta.get("categories"),
        "check_note": "",
        "tokens_input": metrics["tokens_input"], "tokens_output": metrics["tokens_output"],
        "tokens_reasoning": metrics["tokens_reasoning"],
        "tokens_cache_read": metrics["tokens_cache_read"], "cost": metrics["cost"],
        "steps": metrics["steps"],
        "error": res.get("error"),
    }


def evaluate_run(run_name, llm=None, workers=8):
    """`llm` is an LLMVerifier or None (llm_verifier questions are then left unscored)."""
    run_dir = resolve_run_dir(run_name)
    key, questions = load_answer_key(), load_questions()
    results, wdirs = load_results(run_dir), worker_dirs(run_dir)

    records = []
    for qid, k in key.items():
        wd = wdirs.get(qid)
        metrics = parse_worker_log(wd / "worker.log" if wd else None)
        records.append(_row(qid, k, questions.get(qid, {}), results.get(qid, {}), metrics))

    pending = []
    for r in records:
        mode, answer = r["eval_mode"], r["answer"]
        if answer is None:
            r["correctness"], r["check_note"] = False, f"no answer (status={r['status']})"
        elif mode == "range_verifier":
            r["correctness"], r["check_note"] = verify_range(answer, r["ideal"])
        elif mode == "str_verifier":
            r["correctness"], r["check_note"] = verify_str(answer, r["ideal"])
        elif mode == "llm_verifier":
            pending.append(r)
        else:
            raise ValueError(f"unknown eval_mode {mode!r} for {r['question_id']}")

    if pending and llm is None:
        for r in pending:
            r["llm_evaluation"] = "skipped (no LLM verifier)"
    elif pending:
        def judge(r):
            return llm.verify(r["question_content"], r["ideal"], r["answer"])
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for r, (ok, why) in zip(pending, ex.map(judge, pending)):
                r["correctness"], r["llm_evaluation"] = ok, why

    return RunEval(run_name=run_dir.name, run_dir=str(run_dir), records=records,
                   judge_model=llm.model if llm else None)
