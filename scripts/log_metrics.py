"""Wall-clock time and token usage of a worker, from its opencode-style worker.log (JSONL)."""
import json

EMPTY = {"time_sec": None, "tokens_total": None, "tokens_input": None, "tokens_output": None,
         "tokens_reasoning": None, "tokens_cache_read": None, "tokens_cache_write": None,
         "cost": None, "steps": None}


def parse_worker_log(path):
    """time_sec = last event ts - first event ts (ms timestamps).
    Tokens are summed over `step_finish` events; tokens_total = input + output + reasoning
    + cache read + cache write. Returns EMPTY-shaped dict with None if the log is missing."""
    if path is None or not path.exists():
        return dict(EMPTY)
    ts, tok, cost, steps = [], dict(input=0, output=0, reasoning=0, cr=0, cw=0), 0.0, 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(ev.get("timestamp"), (int, float)):
            ts.append(ev["timestamp"])
        if ev.get("type") == "step_finish":
            part = ev.get("part", {})
            t = part.get("tokens") or {}
            cache = t.get("cache") or {}
            tok["input"] += t.get("input", 0)
            tok["output"] += t.get("output", 0)
            tok["reasoning"] += t.get("reasoning", 0)
            tok["cr"] += cache.get("read", 0)
            tok["cw"] += cache.get("write", 0)
            cost += part.get("cost") or 0.0
            steps += 1
    if not ts:
        return dict(EMPTY)
    return {"time_sec": round((max(ts) - min(ts)) / 1000, 1),
            "tokens_total": sum(tok.values()), "tokens_input": tok["input"],
            "tokens_output": tok["output"], "tokens_reasoning": tok["reasoning"],
            "tokens_cache_read": tok["cr"], "tokens_cache_write": tok["cw"],
            "cost": round(cost, 6), "steps": steps}
