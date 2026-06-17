"""The LOOP-1 iteration -- the inner loop that grows the player.

One iteration: select a parent from the archive -> evaluate it across worlds (run plays, score
each with the lab) -> meta-edit it into a child -> evaluate the child -> admit to the archive.
The judge is the lab's band score; the scarce resource is the probe budget, not turns.

This is the orchestration spine. It is deliberately kept distinct from `hta/gym/loop.py`: the
two loops read alike at the bullet-point level but diverge in the middle -- LOOP 1's evaluate
is *run live episodes and average the band score* (expensive, stochastic), LOOP 2's gate is
*re-derive the grade mechanically* (free, deterministic). Sharing only the archive primitive
beneath them keeps that asymmetry legible.

Stub: the iteration lands when the play, report, meta, and lab grader are wired (the reference
is `run_iteration` in hta/_trail/loop.py).
"""

from __future__ import annotations

from hta.config import Config


def run_iteration(cfg: Config, iteration: int) -> dict:
    """Run one LOOP-1 iteration; return its outcome record. See module docstring for the steps."""
    raise NotImplementedError("the iteration lands when LOOP 1 is wired")
