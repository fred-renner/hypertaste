"""WiltWorld: a single hidden-rule world + objective scorer.

The world owns the hidden rule. It hands the agent a ProbeChannel (booleans only)
and, after the agent guesses, scores the guess by *empirical equivalence*: the
guessed lambda is equivalent to the hidden rule iff they agree on a fixed,
deterministic battery of test inputs (WILT's "same or equivalent" criterion).

Equivalence checking and info-gain computation happen here, in the world plane,
never in the agent's reach.
"""

import random
from typing import List, Optional

from .channel import ProbeChannel
from .grammar import RuleSpec, compile_rule, candidate_library, consistent_candidates


def _battery(seed: int = 0) -> List[tuple]:
    """Deterministic battery of triples spanning small ints, negatives, zeros,
    decimals, and structural edge cases (equal/boundary values)."""
    rng = random.Random(seed)
    pts = set()
    # structured edge cases
    base = [-5, -2, -1, 0, 1, 2, 3, 5, 10]
    for a in base:
        for b in base:
            for c in base:
                pts.add((a, b, c))
    # a few decimals and larger magnitudes
    for _ in range(120):
        t = tuple(rng.choice([-9.9, -3, -1.5, 0, 0.5, 1.5, 4, 7, 12, 99]) for _ in range(3))
        pts.add(t)
    return sorted(pts, key=lambda p: (p[0], p[1], p[2]))


_BATTERY = _battery()


class WiltWorld:
    def __init__(self, rule: RuleSpec, max_probes: int = 30):
        self.rule = rule
        self.max_probes = max_probes

    @property
    def name(self) -> str:
        return self.rule.name

    def open_channel(self) -> ProbeChannel:
        return ProbeChannel(self.rule.fn, self.max_probes)

    # ---- scoring (world plane) ----
    def score_guess(self, guess_src: Optional[str]) -> dict:
        """Return {'solved': bool, 'agreement': float, 'valid': bool}.
        solved == empirically equivalent to the hidden rule on the battery."""
        if not guess_src:
            return {"solved": False, "agreement": 0.0, "valid": False}
        try:
            gfn = compile_rule(guess_src)
        except ValueError:
            return {"solved": False, "agreement": 0.0, "valid": False}
        agree = 0
        for t in _BATTERY:
            if gfn(*t) == self.rule.fn(*t):
                agree += 1
        agreement = agree / len(_BATTERY)
        return {"solved": agreement == 1.0, "agreement": agreement, "valid": True}

    # ---- info-gain ground truth (taste plane helper; agent-inaccessible) ----
    def hypothesis_reduction(self, history) -> dict:
        """How much the probes narrowed the candidate hypothesis space.
        Uses the candidate library as the measurable hypothesis space."""
        lib = candidate_library()
        start = len(lib)
        # progressive: consistent set after each prefix of history
        sizes = [start]
        for i in range(1, len(history) + 1):
            sizes.append(len(consistent_candidates(history[:i], lib)))
        end = sizes[-1]
        reduced = (start - end) / start if start else 0.0
        # average per-probe fractional reduction (rewards splitting probes)
        per_probe = []
        for i in range(1, len(sizes)):
            if sizes[i - 1] > 0:
                per_probe.append((sizes[i - 1] - sizes[i]) / sizes[i - 1])
        avg_gain = sum(per_probe) / len(per_probe) if per_probe else 0.0
        return {"start": start, "end": end, "reduced_frac": reduced, "avg_info_gain": avg_gain}
