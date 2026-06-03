"""Seed task-agent program (the unit that evolves).

Contract (the meta agent must preserve this):
    class Solver:
        def run(self, channel, llm) -> str   # returns a python lambda string (the guess)

It interacts with the world ONLY through `channel` (probe results are booleans) and
thinks ONLY through `llm` (a constrained-generation call bound to the task model,
Haiku). It must not import any world/engine internals.

`STRATEGY` is a coarse behavior knob the meta agent can rewrite ("naive" ->
confirmation-biased; "smart" -> falsification + Occam). A real meta agent is free to
replace this whole file with something better, as long as the contract holds.
"""

import json
import re

STRATEGY = "naive"   # meta agent may change this and/or rewrite the strategy below.


def _extract_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_]*|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def _valid_triple(p):
    return (isinstance(p, (list, tuple)) and len(p) == 3
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in p))


class Solver:
    def run(self, channel, llm):
        history = []  # list of {"triple": [...], "label": bool}
        seen = set()
        while channel.remaining() > 0:
            probe = self._next_probe(history, channel.remaining(), llm)
            if probe is None or tuple(probe) in seen:
                probe = self._fallback_probe(history, seen)
            seen.add(tuple(probe))
            label = channel.probe(probe)
            history.append({"triple": list(probe), "label": bool(label)})
        return self._guess(history, llm)

    # ---- probing ----
    def _next_probe(self, history, remaining, llm):
        ctx = json.dumps({"role": "probe", "strategy": STRATEGY,
                          "remaining": remaining, "history": history})
        if STRATEGY == "smart":
            guidance = ("Propose a test case that could DISPROVE your current best "
                        "hypothesis. Seek diverse and edge cases: equal values, "
                        "negatives, zero, non-strict orderings, large gaps. Never "
                        "repeat a previous test case.")
        else:
            guidance = ("Propose another test case similar to ones that returned True, "
                        "to confirm your current hypothesis.")
        prompt = (
            "You are discovering a hidden rule that maps three numbers to True/False "
            "(Wason 2-4-6 task). Here are your observations so far:\n"
            f"{self._fmt_history(history)}\n\n{guidance}\n"
            'Respond ONLY with JSON: {"probe": [x, y, z]}\n'
            f"<<CTX>>{ctx}<<CTX>>"
        )
        probe = (_extract_json(llm(prompt, role="probe")) or {}).get("probe")
        return probe if _valid_triple(probe) else None

    def _fallback_probe(self, history, seen):
        n = len(history)
        for cand in ([n + 1, n + 2, n + 3], [n, n, n], [-n - 1, 0, n + 1], [n + 3, n + 1, n]):
            if tuple(cand) not in seen:
                return cand
        return [n + 7, n + 11, n + 13]

    # ---- guessing ----
    def _guess(self, history, llm):
        ctx = json.dumps({"role": "guess", "strategy": STRATEGY, "history": history})
        emphasis = ("Return the SIMPLEST rule consistent with ALL observations "
                    "(Occam's razor)." if STRATEGY == "smart"
                    else "Return your best guess for the rule.")
        prompt = (
            "You have finished probing the hidden rule. Observations:\n"
            f"{self._fmt_history(history)}\n\n{emphasis}\n"
            "The rule is a Python lambda over x, y, z returning a bool.\n"
            'Respond ONLY with JSON: {"rule": "lambda x, y, z: ..."}\n'
            f"<<CTX>>{ctx}<<CTX>>"
        )
        rule = (_extract_json(llm(prompt, role="guess")) or {}).get("rule")
        if isinstance(rule, str) and rule.strip().startswith("lambda"):
            return rule.strip()
        return "lambda x, y, z: x < y < z"

    @staticmethod
    def _fmt_history(history):
        if not history:
            return "  (none yet)"
        return "\n".join(f"  {tuple(h['triple'])} -> {h['label']}" for h in history)
