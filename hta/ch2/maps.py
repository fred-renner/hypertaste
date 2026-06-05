"""The hand-built tiny grammar-maps for the thin slice (not loop-generated).

Three small tapes chosen to stress the two bets and the deception axis:

- `ramp_clean` : equal-ish segments, one of each family member — the clean ramp/VoI case.
- `decoy`      : a long boring `const` segment (high value, low novelty) next to short
                 flashy high-step `arith`/`alt` segments (low value, high novelty). The
                 locally-attractive probe is wrong: only reading 'this is long, pin it
                 first' wins. Deception, à la novelty-search.
- `tight`      : K=3, three equal segments — a symmetric ramp sanity check.

Budgets are deliberately scarce (a probe set cannot pin every segment) so the oracle must
choose and the gap to a no-inference walker is real.
"""

from .grammar import Segment, TapeSpec

MAPS = [
    TapeSpec(
        name="ramp_clean", K=4, budget=8,
        segments=(
            Segment("const", (2,), 6),
            Segment("arith", (1, 1), 5),
            Segment("alt", (0, 3), 4),
            Segment("arith", (3, 2), 3),
        ),
    ),
    TapeSpec(
        name="decoy", K=4, budget=7,
        segments=(
            Segment("const", (1,), 8),     # long + boring -> the high-value target
            Segment("arith", (0, 3), 3),   # short + flashy (big step) -> shiny dead-end
            Segment("alt", (2, 0), 5),
            Segment("arith", (1, 2), 2),   # short + flashy
        ),
    ),
    TapeSpec(
        name="tight", K=3, budget=6,
        segments=(
            Segment("const", (1,), 5),
            Segment("arith", (0, 1), 5),
            Segment("alt", (2, 1), 5),
        ),
    ),
]


def by_name(name: str) -> TapeSpec:
    for m in MAPS:
        if m.name == name:
            return m
    raise KeyError(name)
