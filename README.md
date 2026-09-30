# BixBench-78 evaluator

Scores agent runs on the 78-question BixBench subset against `src/answers_78.json`.

```
python run_eval.py baseline              # evaluates run_output/baseline
python run_eval.py out1 out2 out3        # several runs; each gets its own report
python run_eval.py baseline --skip-llm   # skip DeepSeek-judged questions
```

Setup (Python 3.10+):
```
python3 -m venv .venv && source .venv/bin/activate
```
Then copy `.env.example` to `.env` and set `DEEPSEEK_API_KEY` (only needed for `llm_verifier` questions;
stdlib only, no pip installs).

## Layout
- `run_eval.py` – runner. `scripts/` – loader, verifiers, DeepSeek client, report writer.
- `src/answers_78.json` – answer key; `src/questions_78.json` – question text (recovered from worker logs
  with `python -m scripts.extract_questions run_output/<run>`; 4 entries come from agent docstrings, see `source`).
- `run_output/<run>/` – run export (`results/all_results.json`, `workers/q*/worker.log`); git-ignored.
- `report/<run>/results.csv` + `summary.json` – output; git-ignored. `.cache/llm_verdicts.json` caches judge verdicts.

## Eval modes
- `range_verifier`: answer must be a single number (trailing `%` ok) inside the closed ideal range.
- `str_verifier`: case/whitespace-insensitive exact match, or the same plain number (`19,159` == `19159`).
- `llm_verifier`: DeepSeek judges question + ideal + answer (temperature 0, JSON verdict).
- Questions with no answer (unresolved) are incorrect. Judge failures leave `correctness` blank ("unscored").

## Metrics
From `worker.log`: `time_sec` = last − first event timestamp; `tokens_total` = input + output + reasoning
+ cache read + cache write, summed over steps (components are separate CSV columns).
