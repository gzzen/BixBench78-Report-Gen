"""One-off helper: recover the question text of each worker from a run's worker.log.

The run output does not ship the question set, but every worker reads its own
questions_open.json during the run, so the text is embedded in worker.log
(either as raw JSON from a shell `cat`, or as numbered lines from a file-read tool).

Usage:  python -m scripts.extract_questions run_output/baseline [-o src/questions_78.json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_NUMBERED = re.compile(r"^\s*\d+:\s?", re.M)


def _iter_tool_outputs(log_path):
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "tool_use":
            out = ev.get("part", {}).get("state", {}).get("output")
            if isinstance(out, str):
                yield out


def _parse_questions_json(text):
    """Find a JSON list of question dicts inside a tool output."""
    text = _NUMBERED.sub("", text) if re.search(r"^\s*1:\s*\[", text, re.M) else text
    start = text.find("[")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                esc = (c == "\\" and not esc)
                if c == '"' and not esc:
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
                    if data and isinstance(data[0], dict) and "question" in data[0]:
                        return data
                    break
        start = text.find("[", start + 1)
    return None


def extract_from_worker(worker_dir):
    for out in _iter_tool_outputs(worker_dir / "worker.log"):
        if '"question_id"' not in out:
            continue
        data = _parse_questions_json(out)
        if data:
            return data[0]
    return None


def _docstring_fallback(worker_dir):
    """Last resort: the "Question ...:" paragraph of the agent script docstring.

    Workers paraphrase/re-wrap it, so it is flagged as non-verbatim in the output.
    """
    for py in (worker_dir / "agents").glob("*.py"):
        m = re.search(r'Question[^:\n]*:[ \t]*\n?(.*?)\n[ \t]*\n', py.read_text(), re.S)
        if m:
            return " ".join(m.group(1).split()).strip('"')
    return None


def extract_run(run_dir):
    questions, missing = {}, []
    for wd in sorted((run_dir / "workers").glob("q*")):
        qid = re.sub(r"^q\d+_", "", wd.name)
        qid = re.sub(r"^(bix)_(\d+)_q(\d+)$", r"\1-\2-q\3", qid)
        meta = extract_from_worker(wd)
        if meta:
            questions[meta["question_id"]] = {
                "capsule": meta.get("short_id"),
                "categories": meta.get("categories"),
                "question": meta["question"],
                "source": "worker.log",
            }
            continue
        text = _docstring_fallback(wd)
        if text:
            questions[qid] = {"capsule": qid.rsplit("-q", 1)[0], "categories": None,
                              "question": text, "source": "agent_docstring"}
        else:
            missing.append(qid)
    return questions, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=ROOT / "src" / "questions_78.json")
    args = ap.parse_args(argv)
    questions, missing = extract_run(args.run_dir)
    ordered = dict(sorted(questions.items(), key=lambda kv: [int(x) for x in re.findall(r"\d+", kv[0])]))
    args.out.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fallback = [q for q, v in ordered.items() if v["source"] != "worker.log"]
    print(f"wrote {len(ordered)} questions to {args.out}")
    print(f"docstring fallback (not verbatim): {fallback}")
    print(f"missing: {missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
