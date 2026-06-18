"""The world-smith -- propose world STRUCTURE, never the score.

This pass ships only the **deterministic mutation operators**: small, mechanical edits to a spec
that produce a spread of variant worlds for the ship-gate to admit or reject. They are NOT the LLM
inventor (that is a later pass) -- they exist to exercise the gate across a known admit/reject
spread, the way the trail hand-authored its structural moves before any live inventor.

Each operator is a pure function `spec -> spec` over the declarative data (safe-eval: data in, data
out, never executed). Its output is a spec the gym validates and gates; the smith asserts nothing
about difficulty or score. The operators assume the seed's canonical layout (bait variables first,
then the prerequisite path: start, then width-2 layers), which every operator preserves, so a whole
lineage of descendants stays well-formed.

The moves, derived from what the grammar's parts can vary:
  * **add_bait / drop_bait** -- more or fewer immediate-coverage readouts (changes the floor and the
    opportunity cost of scouting).
  * **deepen / flatten** -- lengthen or shorten the prerequisite path (compounding horizon). Deepen
    = earned access one step further out (still ships, harder); flatten toward a single hop = a
    payoff a 2-step planner can see (the gate should reject it as trivial).
  * **tighten_budget / loosen_budget** -- the scarcity dial. Tighten until the fix cannot reach the
    band (the gate should reject it as unsolvable); loosen until a planner can complete the path.

Model-free -- it must never import hta.llm. Reference: `propose_move`/`realize_proposal` in
hta/_trail/world_smith.py (the live-inventor scaffold lands with that later pass).
"""

from __future__ import annotations

from typing import List, Mapping


def _params(spec: Mapping) -> dict:
    """Read a canonical spec back into its generating parameters (bait count, path depth, payoff
    weight, budget). Depth = 1 + number of hops (variables pinned on any walk)."""
    return {
        "n_bait": len(spec["bait"]),
        "depth": 1 + len(spec["payoff"]["hops"]),
        "weight": int(spec["payoff"]["weight"]),
        "budget": int(spec["budget"]),
    }


def compose(n_bait: int, depth: int, weight: int, budget: int, name: str = "spec") -> dict:
    """Build a canonical spec from its parameters. Variable layout: 0..n_bait-1 bait; then the path
    start; then (depth-1) width-2 layers (each hop maps the current variable's value to one of the
    next layer's two variables). This is the one layout the operators read and write."""
    start = n_bait
    nxt = n_bait + 1
    hops = []
    for _ in range(depth - 1):
        hops.append([nxt, nxt + 1])
        nxt += 2
    return {
        "name": name, "n_vars": nxt, "K": 2, "budget": budget,
        "bait": list(range(n_bait)),
        "payoff": {"start": start, "hops": hops, "weight": weight},
    }


def _mutate(spec: Mapping, *, d_bait=0, d_depth=0, d_weight=0, d_budget=0, tag: str) -> dict:
    p = _params(spec)
    return compose(
        n_bait=p["n_bait"] + d_bait,
        depth=p["depth"] + d_depth,
        weight=p["weight"] + d_weight,
        budget=p["budget"] + d_budget,
        name=f"{spec.get('name', 'spec')}+{tag}",
    )


def add_bait(spec: Mapping) -> dict:
    return _mutate(spec, d_bait=1, tag="bait")


def drop_bait(spec: Mapping) -> dict:
    return _mutate(spec, d_bait=-1, tag="debait")


def deepen(spec: Mapping) -> dict:
    """Lengthen the prerequisite path by one layer -- earned access one horizon further out. Bumps
    the budget in step (as the trail co-evolved budget with depth: a longer scout still needs room
    for light mop-up), so a deepened world is *harder* (a deeper horizon), not merely budget-starved."""
    return _mutate(spec, d_depth=1, d_budget=1, tag="deepen")


def flatten(spec: Mapping) -> dict:
    """Shorten the prerequisite path by one layer -- toward a payoff a shallow planner can see."""
    return _mutate(spec, d_depth=-1, tag="flatten")


def tighten_budget(spec: Mapping) -> dict:
    return _mutate(spec, d_budget=-1, tag="tight")


def loosen_budget(spec: Mapping) -> dict:
    return _mutate(spec, d_budget=1, tag="loose")


OPERATORS = [add_bait, drop_bait, deepen, flatten, tighten_budget, loosen_budget]


def spread(spec: Mapping) -> List[dict]:
    """Apply every operator once to `spec`, returning the variant specs (a deterministic spread for
    the ship-gate to admit/reject). The smith proposes structure only -- no score field is ever
    emitted (an integrity invariant the tests assert)."""
    return [op(spec) for op in OPERATORS]
