"""The hand-built tiny grammar-maps for the thin slice (not loop-generated).

These are the *deceptive* maps (WORLD_DESIGN.md -> "First slice", iteration 1). The first
maps were too transparent — boundaries were handed to the agent and a 3-member family let
"probe 2-3 cells per known segment and extrapolate" trivially win, so even a bare prompt did
the value-of-information move and the taste gap drowned in noise. These rebuild deception in:

- **Hidden boundaries.** The agent is NOT told how many segments there are or where they
  split (only the family + tape length). Segmentation must be *inferred* from the structure.
- **The arith/cycle mirage.** `cycle(a,b,c)` and `arith(a, b-a)` share the same 3-cell
  prefix, so a cheap local read extrapolates confidently WRONG; only a far confirm-probe
  tells them apart. The locally-attractive move is wrong exactly where it counts.
- **The boring-door decoy.** A long low-novelty `const` run is the highest-value target
  (many cells per probe) but looks dull; short flashy segments lure a curiosity walker into
  spending its scarce budget where the cells are few.

Maps (under hidden boundaries):
- `decoy`  : a short flashy `cycle` lure, then the long boring `const` prize, then more
             flashy short segments. Reading "this dull run is long, pin its extent first"
             wins; chasing the shiny cells loses.
- `mirage` : a fat boring `const` bank (the prize), then an `arith` run and a `cycle` run
             with the SAME [0,1,2] prefix back to back (the lure). Banking the dull run wins;
             pouring probes into the flashy mirage — where a local read mistakes one pattern
             for the other and only the global period (does [0,1,2] repeat?) disambiguates —
             loses.
- `tight`  : K=4, three equal segments spanning const/cycle/alt — a symmetric ramp sanity
             check, still requiring boundary inference and a cycle confirm-probe.

Budgets are deliberately scarce (a probe set cannot pin every segment) so the oracle must
choose and the gap to a no-inference walker is real.
"""

from .grammar import Segment, TapeSpec

MAPS = [
    TapeSpec(
        name="decoy", K=4, budget=7,
        segments=(
            Segment("cycle", (0, 1, 2), 3),   # [0,1,2] short flashy lure (looks like arith)
            Segment("const", (2,), 8),        # [2x8] long + boring -> the high-value prize
            Segment("arith", (3, 1), 4),      # [3,0,1,2] flashy wrapping run
            Segment("alt", (1, 3), 3),        # [1,3,1] short flashy
        ),
    ),
    TapeSpec(
        name="mirage", K=4, budget=7,
        segments=(
            Segment("const", (2,), 7),        # [2x7] the fat boring bank -> the real prize
            Segment("arith", (0, 1), 4),      # [0,1,2,3] arith with the [0,1,2] prefix
            Segment("cycle", (0, 1, 2), 4),   # [0,1,2,0] same prefix, but it REPEATS (the lure)
        ),
    ),
    TapeSpec(
        name="tight", K=4, budget=6,
        segments=(
            Segment("const", (1,), 5),
            Segment("cycle", (2, 0, 3), 5),   # [2,0,3,2,0] period-3 needs a confirm-probe
            Segment("alt", (3, 1), 5),
        ),
    ),
]


def by_name(name: str) -> TapeSpec:
    for m in MAPS:
        if m.name == name:
            return m
    raise KeyError(name)
