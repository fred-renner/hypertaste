"""The instruments -- proof that taste is climbing, not that the score is being gamed.

These are read-only measurements taken *alongside* selection, never inputs to it:
  - held-out climb   -- score on a disjoint draw set the loop never selected on.
  - standing baseline -- a vanilla (un-evolved) player, the lazy constant to beat.
  - port check       -- the evolved playbook run on a *different, weaker* model (the transfer
                        thesis: taste should ride onto a weak model).
  - vocabulary watch -- scan the playbook text for leaked world-internals.

INVARIANT (the mirror of the scorer): the scorer *drives* selection and is agent-inaccessible;
these *observe* selection and must be selection-INACCESSIBLE -- if they feed the fitness that
picks parents, they rot into targets (DESIGN.md). Keeping them physically out of `loop.py` is
the lintable expression of "read-only to selection."

Stub: built incrementally as LOOP 1 needs each instrument (the held-out split exists in
hta/_trail/loop.py; the rest are new). The port check is the load-bearing one for the thesis.
"""

from __future__ import annotations


def held_out_climb(node: object) -> float:
    """Score on a disjoint, never-selected-on draw set. Observed, never optimized."""
    raise NotImplementedError("lands with LOOP 1")


def port_check(node: object) -> float:
    """Run the evolved playbook on a different/weaker model -- the transfer thesis."""
    raise NotImplementedError("lands with LOOP 1")
