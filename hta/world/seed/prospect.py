"""The hand-authored seed world -- the smith's worked example, a real parts-list in the language
(DESIGN.md sec.7: "author instance 0 as a real parts-list ... so it's the smith's worked example,
not a throwaway"). It is one *instance* of the `prospect` family (hta/world/spec.py); the smith
will write others, and this one is disposable.

What it plants (the taste the floor->oracle gap rewards, never written as a rule -- DESIGN sec.4
"plant the condition, never the response"):

  * a fixed `clearing` block (reg 0) -- immediate-payoff BAIT. A lazy player grabs it (it sets the
    floor); a myopic/greedy player over-invests in it and never starts the deep work (deception).
  * a `vein` -- a depth-2 inference seam (pointer reg 2 -> ore pool {3,4}). *Which* ore is live is
    the hidden pointer value, fresh every episode, so you read the position to pick the probe; the
    payoff pays nothing until pointer AND ore both land. Mining it beats a myopic planner.
  * a `prospect` -- a graded, depth-3 seam (assay reg 5 -> pointer reg 6 -> ore pool {7,8}) with a
    hidden GRADE. Its payoff (8 cells, the richest seam) is worth the most when rich, but barren
    half the time -- and a barren vein mirrors an UNPROBEABLE noise register (reg 9), so it can
    never be pinned. The tasteful move is to assay first and TURN AROUND on a barren vein (the
    learning-gradient / dead-end habit, DESIGN sec.2) rather than sink the deepest shaft into it.

Under a tight budget the player cannot do everything: it must read the cheap evidence, chase the
steep give-back, and abandon the flat vein. The exact oracle (best adaptive play) takes the rich
prospect when the assay says rich and redirects when it says barren; the lazy floor only grabs the
bait; a 1-step greedy never starts a seam at all. That separation is certified mechanically in
tests/test_world_spec.py (grade_world: a wide gap and reachable in budget; and oracle > greedy).

Register map (R=10, K=2, one role per register): 0,1 clearings (each a 2-cell bait block) |
2 vein-pointer, 3/4 vein-ore | 5 prospect-assay, 6 prospect-pointer, 7/8 prospect-ore,
9 prospect-noise (UNPROBEABLE -- the barren dead end). No gaps; see spec.validate.
"""

from __future__ import annotations

from typing import Optional

from hta.world.spec import build


def seed_spec() -> dict:
    """The seed world as a declarative spec (plain data -- the safe-eval unit). R=10, K=2 -> 1024
    hypotheses, kept small so the exact oracle stays computable (an invariant). Budget 5 is tight:
    it funds the bait + one deep seam, never everything, so allocation under scarcity binds."""
    return {
        "kind": "prospect",
        "name": "seed-prospect",
        "K": 2,
        "R": 10,
        "budget": 5,
        "clearings": [
            {"reg": 0, "cells": 2, "cost": 1},        # the immediate-payoff bait (sets the floor)
            {"reg": 1, "cells": 2, "cost": 1},
        ],
        "seams": [
            # the vein: always-rich, depth-2 inference (pointer -> ore). 4 payoff cells.
            {"pointer": 2, "ore": [3, 4], "cells": 4},
            # the prospect: graded (assay), depth-3, the richest seam (8 cells) but barren half the
            # time -- a barren payoff mirrors the unprobeable noise reg 9, so it is a real dead end.
            {"assay": 5, "pointer": 6, "ore": [7, 8], "noise": 9, "cells": 8},
        ],
    }


def build_seed(seed: int = 0):
    """Build the seed world with its hidden answer drawn from `seed` (harness-side; see spec.build)."""
    return build(seed_spec(), seed=seed)
