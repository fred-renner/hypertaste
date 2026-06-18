"""The seed world -- the grammar's unit test, authored IN the grammar (not a showcase).

A grammar invented purely in the abstract fails two ways: too **weak** (every world it can express
is solved by grabbing the nearest payoff -> no look-ahead ever required -> no taste in anything it
builds) or too **loose** (it lets you write a world the dumb scorer cannot grade). So we author one
seed that pushes the exact property we care about -- *can this vocabulary express a world that
genuinely forces allocation under scarcity and still be graded mechanically?* -- and certify it
against the frozen grader + the dumb-player battery. The world is the **test** of the grammar, never
its source (findings/2026-06-18-world-building-substrate.md).

`seed_spec()` is the smallest world that genuinely demands multi-horizon allocation under scarcity,
spelled entirely in the part box (`hta/world/spec.py`):

  * **4 immediate readouts** (bait) -- each pays one coverage cell the moment you probe it.
  * **a gated payoff worth 5 cells**, earned only by a depth-3 prerequisite walk: read the start
    variable (it names which of two middle variables is live), read that (it names which of two
    target variables is live), read that -- and only then does the 5-cell payoff fall out. Every
    step on the walk is a gate readout that pays ZERO coverage; no single probe pins the payoff.
  * **budget 4 == the bait count** -- the scarcity. The budget fits *scout (3) + one bait mop-up*,
    but NOT *grab all four bait*; and spending a probe on a zero-coverage gate has a strict
    opportunity cost (there are exactly as many bait as the budget). Grabbing the bait is the trap.

Certified offline, model-free (see tests/): floor 4 -> oracle 6 (gap 2, reachable 0.67) -- `hard`
and `solvable` per the frozen grader; the gated payoff sits a step deeper than a 2-move planner can
see, so best-play clears the whole battery by a wide margin (lookahead-2 stalls at 4.5, margin
0.75); and the ZPD bracket is clean -- the greedy champion analogue stalls at the floor while the
scout-the-path fix reaches the oracle band. That separation is *room for taste* in the world's
geometry, agent-independent; whether a live champion sits in it is LOOP 1's call, not this pass's.
"""

from __future__ import annotations


def seed_spec() -> dict:
    """The certified seed spec, as plain data (the safe-eval form). Variable layout: 0..3 bait;
    4 = the path start; 5,6 = the two middle variables; 7,8 = the two target variables."""
    return {
        "name": "seed",
        "n_vars": 9,
        "K": 2,
        "budget": 4,
        "bait": [0, 1, 2, 3],
        "payoff": {
            "start": 4,
            "hops": [[5, 6],    # start's value selects which middle variable is live
                     [7, 8]],   # the live middle's value selects which target variable is live
            "weight": 5,        # the payoff block: 5 coverage cells, pinned only by the full walk
        },
    }
