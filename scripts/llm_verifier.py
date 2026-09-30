"""LLM-judged verification (eval_mode == llm_verifier) using DeepSeek.

Verdicts are cached on disk keyed by (model, question, ideal, answer, prompt version) so re-running
an evaluation - or comparing runs that share identical answers - never pays twice."""
import hashlib
import json
import threading

from .config import CACHE_DIR
from .deepseek import DeepSeekClient, DeepSeekError

PROMPT_VERSION = "v1"
SYSTEM = (
    "You are a strict grader for a bioinformatics benchmark. Given a question, the reference "
    "(ideal) answer and a candidate answer, decide whether the candidate answer is correct.\n"
    "Rules:\n"
    "- Correct means it conveys the same result as the reference: the same entity/conclusion, or a "
    "number that agrees with the reference to the precision the reference implies "
    "(e.g. 0.3050 vs 0.26 is wrong; 93.98% vs 94% is right).\n"
    "- Ignore differences in wording, capitalisation, units formatting and extra explanation, "
    "as long as they do not change the result.\n"
    "- If the candidate hedges between several different answers, or gives no answer, it is incorrect.\n"
    "- Never reward reasoning quality; judge only the final answer against the reference.\n"
    'Reply with JSON only: {"correct": true|false, "reasoning": "<one or two sentences>"}'
)


def _key(model, question, ideal, answer):
    raw = json.dumps([PROMPT_VERSION, model, question, ideal, answer], ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


class LLMVerifier:
    def __init__(self, client=None):
        self.client = client or DeepSeekClient()
        self._path = CACHE_DIR / "llm_verdicts.json"
        self._lock = threading.Lock()
        try:
            self._cache = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._cache = {}

    @property
    def model(self):
        return self.client.model

    def _save(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._cache, indent=1, ensure_ascii=False), encoding="utf-8")

    def verify(self, question, ideal, answer):
        """Return (correct: bool|None, evaluation: str). None means the judge call failed."""
        if answer is None:
            return False, "no answer"
        key = _key(self.model, question, ideal, answer)
        with self._lock:
            hit = self._cache.get(key)
        if hit:
            return hit["correct"], hit["reasoning"]
        user = f"Question:\n{question}\n\nReference answer:\n{ideal}\n\nCandidate answer:\n{answer}"
        try:
            text, _usage = self.client.chat(
                [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                json_mode=True)
            data = json.loads(text)
            correct, reasoning = bool(data["correct"]), str(data.get("reasoning", "")).strip()
        except (DeepSeekError, json.JSONDecodeError, KeyError, TypeError) as e:
            return None, f"judge error: {e}"
        with self._lock:
            self._cache[key] = {"correct": correct, "reasoning": reasoning}
            self._save()
        return correct, reasoning
