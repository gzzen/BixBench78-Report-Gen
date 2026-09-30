#!/usr/bin/env python3
"""Evaluate BixBench-78 run output(s) against src/answers_78.json.

    python run_eval.py baseline                 # one run in run_output/baseline
    python run_eval.py out1 out2 out3           # several runs, each evaluated + reported
    python run_eval.py baseline --skip-llm      # don't call DeepSeek (llm questions left unscored)

Each run writes report/<run_name>/results.csv and report/<run_name>/summary.json.
Judge settings (DEEPSEEK_API_KEY, ...) are read from .env.
"""
import argparse
import sys

from scripts.deepseek import DeepSeekError
from scripts.evaluate import evaluate_run
from scripts.llm_verifier import LLMVerifier
from scripts.report import write_report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", help="run names in run_output/ (or paths to run directories)")
    ap.add_argument("--skip-llm", action="store_true", help="skip llm_verifier questions")
    ap.add_argument("--workers", type=int, default=8, help="parallel LLM judge calls")
    args = ap.parse_args(argv)

    llm = None
    if not args.skip_llm:
        try:
            llm = LLMVerifier()
        except DeepSeekError as e:
            print(f"warning: {e}\n         llm_verifier questions will be left unscored "
                  f"(use --skip-llm to silence)", file=sys.stderr)

    evals = {}
    for name in args.runs:
        ev = evaluate_run(name, llm=llm, workers=args.workers)
        out, s = write_report(ev)
        evals[ev.run_name] = ev
        print(f"[{ev.run_name}] {s['n_correct']}/{s['n_questions']} correct "
              f"({s['accuracy']:.1%}), unscored={s['n_unscored']} -> {out}")
        for mode, m in s["by_eval_mode"].items():
            print(f"    {mode:15s} {m['correct']:>3}/{m['n']:<3} unscored={m['unscored']}")

    # Cross-run comparison hook: `evals` maps run_name -> RunEval (records are per-question
    # dicts keyed by question_id), which is all a future scripts/compare.py needs.
    return 0


if __name__ == "__main__":
    sys.exit(main())
