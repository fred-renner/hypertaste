"""The hand-built tiny grammar-maps for the thin slice (not loop-generated).

These are the *distributed-value* maps (WORLD_DESIGN.md -> "Third slice"). The second-slice
maps fixed the transparency problem (hidden boundaries + the arith/cycle mirage), but bet 1
still failed on aggregate for an understood reason: the taste gap's sign tracked **value-
spread**. Where value sat behind several confirm-requiring segments the hand prompt won; where
a single fat `const` dominated, a naive prober banked it cheaply in one local read and the
taste prompt's blanket spread-and-confirm was dead-weight, so taste *lost*. Tuning maps until
the gap turned positive would be optimizing toward the instrument; instead these maps are
rebuilt on a principle:

- **Distributed value, no trivially-bankable segment.** No `const` at all, and no single
  segment is more than ~35% of the tape (`maxfrac < 0.4`). Value is spread across several
  segments that each demand real inference, so taste's discipline pays *everywhere* rather than
  being overhead next to one free prize.
- **Value sits behind the mirage.** The dominant segments are an `arith`/`cycle` pair sharing
  the same `[a, a+s, a+2s]` prefix: a local read mistakes one for the other and forfeits the
  whole run; only a far confirm-probe disambiguates. The `alt` runs use a value-difference of
  1 or 3 (not 2, which collides with an arith step) so they too need a third probe, not two.
- **Hidden boundaries.** The agent is told the family + tape length only — never the segment
  count or the splits — so segmentation must be inferred by spreading probes.

Maps (all K=4, const-free):
- `twin`  : a long `arith` then a long `cycle` BACK TO BACK, both opening `[0,1,2]`, plus an
            `alt` tail. Two long ambiguous runs whose shared boundary is itself camouflaged;
            the confirm-probe is the whole game.
- `braid` : the mirage pair flipped (a long `cycle` then a long `arith`, opening `[1,2,3]`) +
            an `alt`. Same lesson, different prefix and order, so a win on both is robustness,
            not a single layout.
- `fan`   : value spread across FOUR shorter segments (an `arith`/`cycle` mirage pair + two
            `alt`s) under a budget that pins only ~two — so allocation (which runs to bank)
            joins the confirm-probe as the taste lever.

Budgets are deliberately scarce (a probe set cannot pin every segment) so the oracle must
choose and the gap to a no-inference walker is real, but generous enough that the confirm
discipline can actually be executed (~3 probes per segment the agent means to pin).
"""

from .grammar import Segment, TapeSpec

MAPS = [
    TapeSpec(
        name="twin", K=4, budget=7,
        segments=(
            Segment("arith", (0, 1), 6),    # [0,1,2,3,0,1] opens [0,1,2] -> the mirage prefix
            Segment("cycle", (0, 1, 2), 6),  # [0,1,2,0,1,2] SAME prefix, but repeats (the lure)
            Segment("alt", (3, 0), 5),       # [3,0,3,0,3] diff=3 -> needs a third probe too
        ),
    ),
    TapeSpec(
        name="braid", K=4, budget=7,
        segments=(
            Segment("cycle", (1, 2, 3), 6),  # [1,2,3,1,2,3] opens [1,2,3] (looks like arith)
            Segment("arith", (1, 1), 6),     # [1,2,3,0,1,2] SAME prefix, diverges at cell 3
            Segment("alt", (0, 3), 5),       # [0,3,0,3,0] diff=3 -> needs a third probe
        ),
    ),
    TapeSpec(
        name="fan", K=4, budget=8,
        segments=(
            Segment("arith", (2, 1), 6),     # [2,3,0,1,2,3] opens [2,3,0] -> mirage prefix
            Segment("cycle", (2, 3, 0), 5),  # [2,3,0,2,3] SAME prefix, repeats
            Segment("alt", (1, 2), 4),       # [1,2,1,2] diff=1 -> needs a third probe
            Segment("alt", (0, 1), 4),       # [0,1,0,1] diff=1 -> needs a third probe
        ),
    ),
]


def by_name(name: str) -> TapeSpec:
    for m in MAPS:
        if m.name == name:
            return m
    raise KeyError(name)
