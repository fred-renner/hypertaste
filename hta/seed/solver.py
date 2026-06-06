"""Seed task-agent program (the unit that evolves) -- a NEUTRAL investigator.

It probes an unknown world through `channel` and reasons through `llm` (the task
model, Haiku). It ships with **no pre-loaded research taste**: the prompts below state
the task and ask for a next probe / a final rule, and say nothing about *how* to
investigate well -- no "confirm", no "falsify", no edge-case list, no Occam steering.
Growing taste -- how to allocate a scarce budget, seek disconfirming cases, track
state, decide when to stop -- is the meta agent's job, **discovered from the trajectory
evidence**, never shipped in the seed. A pre-loaded recipe is the null hypothesis
(taste frozen at the designer's articulable ceiling); the seed must be a blank slate so
that any taste the system shows was grown, not installed.

Contract (the meta agent must preserve this):
    class Solver:
        def run(self, channel, llm) -> str   # returns a python lambda string (the guess)

It interacts with the world ONLY through `channel` (probe results are booleans) and
thinks ONLY through `llm`. It must not import any world/engine internals. A real meta
agent is free to replace this whole file with something better, as long as the contract
holds.

`_MOCK_VARIANT` is **not** research content -- it is a hook the deterministic mock
backend reads to simulate a behavior change after a meta edit, so the offline plumbing
is observable. The real task model never sees it, the real prompts below do not branch
on it, and the real meta agent may delete it.
"""

import json
import re

_MOCK_VARIANT = "seed"   # mock-only plumbing fixture; the mock meta edit flips it to "edited".


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
    def episode_prompt(self, max_probes):
        """Single-session mode: build the whole-episode prompt for one world. Loads
        episode_prompt.md (next to this file) and fills in the budget. It carries no
        strategy guidance -- the prompt states the task and the protocol only."""
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "episode_prompt.md")) as f:
            template = f.read()
        return template.format(max_probes=max_probes)

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
        ctx = json.dumps({"role": "probe", "variant": _MOCK_VARIANT,
                          "remaining": remaining, "history": history})
        prompt = (
            "You are investigating a hidden rule that maps three numbers (x, y, z) to "
            "True or False. Your observations so far:\n"
            f"{self._fmt_history(history)}\n\n"
            "Propose the next test case to evaluate.\n"
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
        ctx = json.dumps({"role": "guess", "variant": _MOCK_VARIANT, "history": history})
        prompt = (
            "You have finished investigating the hidden rule. Your observations:\n"
            f"{self._fmt_history(history)}\n\n"
            "State the rule as a Python lambda over x, y, z returning a bool, consistent "
            "with everything you observed.\n"
            'Respond ONLY with JSON: {"rule": "lambda x, y, z: ..."}\n'
            f"<<CTX>>{ctx}<<CTX>>"
        )
        rule = (_extract_json(llm(prompt, role="guess")) or {}).get("rule")
        if isinstance(rule, str) and rule.strip().startswith("lambda"):
            return rule.strip()
        return "lambda x, y, z: True"

    @staticmethod
    def _fmt_history(history):
        if not history:
            return "  (none yet)"
        return "\n".join(f"  {tuple(h['triple'])} -> {h['label']}" for h in history)
