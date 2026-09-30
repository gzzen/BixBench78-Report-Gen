"""Deterministic verifiers for the `range_verifier` and `str_verifier` eval modes.

Each verifier returns (correct: bool, note: str)."""
import re

_NUM = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_PURE_NUM = re.compile(rf"^\s*({_NUM})\s*%?\s*$")


def _clean(s):
    return str(s).replace(",", "").strip()


def parse_range(ideal):
    """'(1.50,1.54)' -> (1.50, 1.54); tolerates inverted bounds (returned sorted)."""
    nums = [float(x) for x in re.findall(_NUM, str(ideal))]
    if len(nums) != 2:
        raise ValueError(f"cannot parse range from {ideal!r}")
    return tuple(sorted(nums))


def verify_range(answer, ideal):
    """Correct iff the answer is a single number (optional trailing %) inside the closed range.
    Answers with several numbers or extra text are rejected rather than guessed at."""
    if answer is None:
        return False, "no answer"
    try:
        lo, hi = parse_range(ideal)
    except ValueError as e:
        return False, str(e)
    swapped = re.findall(_NUM, str(ideal))[0:2]
    note = "ideal range was inverted; bounds sorted" if float(swapped[0]) > float(swapped[1]) else ""
    m = _PURE_NUM.match(_clean(answer))
    if not m:
        return False, "; ".join(x for x in (note, "answer is not a single number") if x)
    val = float(m.group(1))
    ok = lo <= val <= hi
    return ok, "; ".join(x for x in (note, f"value {val:g} vs [{lo:g}, {hi:g}]") if x)


def _norm_str(s):
    return " ".join(str(s).lower().split())


def verify_str(answer, ideal):
    """Correct iff normalised strings are equal (case/whitespace), or both are the same plain number
    (thousands separators and a trailing % are ignored: '19,159' == '19159', '5%' == '5')."""
    if answer is None:
        return False, "no answer"
    if _norm_str(answer) == _norm_str(ideal):
        return True, "exact match"
    a, b = _PURE_NUM.match(_clean(answer)), _PURE_NUM.match(_clean(ideal))
    if a and b and float(a.group(1)) == float(b.group(1)):
        return True, "numeric match"
    return False, "no match"
