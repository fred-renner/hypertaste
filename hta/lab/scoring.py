"""The grader: best-play, lazy-play, score a run, rate a world.

`World` (below) is the short list of questions every world agrees to answer so one grader
fits all of them -- what can be probed, what each probe costs, and (given the hidden
answer) the true value at a position. It is not machinery; it is the shape a built world
presents to the scorer. It earns no file of its own and no jargon ("contract" retired):
it is the input format these functions expect.

The four functions are the whole grading shop:
  - oracle(world)      -> best-possible play: the ceiling (mechanical, deterministic).
  - floor(world)       -> lazy / no-skill play: the bottom.
  - score_run(...)     -> place a player's actual result in the floor->oracle band (LOOP 1).
  - grade_world(world) -> rate difficulty: is the best/lazy gap wide AND the top reachable
                          in budget (LOOP 2's smith). The scorer pointed at a world, not a run.

Stub: the band math + the exact best-play computation land when LOOP 1 is wired (ported
from the worked example in hta/_trail/anchor.py). Per the integrity floor this module is
model-free -- it must never import hta.llm.
"""

from __future__ import annotations

from typing import Protocol, Sequence


class World(Protocol):
    """The questions every world answers so the grader needs no per-world special-casing.

    A *built* world (a validated spec + its drawn hidden answer) implements this. The
    grader reads only these; it never sees the world's internals.
    """

    def positions(self) -> Sequence[object]:
        """The positions a player may probe (the columns the grader reasons over)."""
        ...

    def cost(self, position: object) -> int:
        """What it costs to probe `position` (the budget is the scarce resource)."""
        ...

    def value(self, position: object) -> float:
        """The true value at `position` under this world's hidden answer.

        Hidden-state-bearing: only the harness holds a built world; this is never exposed
        on a player's tool surface. See hta/dgmh/play/server.py for the confined surface.
        """
        ...


def oracle(world: World) -> float:
    """Best-possible expected score under perfect adaptive play. The ceiling."""
    raise NotImplementedError("ported from the worked example when LOOP 1 is wired")


def floor(world: World) -> float:
    """Lazy / no-skill baseline. The bottom of the band."""
    raise NotImplementedError("ported from the worked example when LOOP 1 is wired")


def score_run(world: World, run: object) -> float:
    """Place a player's actual result in the floor->oracle band: 0 = lazy, 1 = oracle."""
    raise NotImplementedError("ported from the worked example when LOOP 1 is wired")


def grade_world(world: World) -> dict:
    """Rate a world's difficulty for the smith: best/lazy gap + solvable-in-budget.

    Returns the verdict LOOP 2 gates on (wide gap => skill matters; reachable top =>
    solvable). The same oracle/floor used by score_run, asked of the world itself.
    """
    raise NotImplementedError("ported from the worked example when LOOP 2 is wired")
