"""The grader: best-play, lazy-play, score a run, rate a world.

`World` (below) is the short list of questions every world agrees to answer so one grader
fits all of them -- what the hidden answer could be, what can be probed, what each probe
costs, what a probe reveals, and which positions count toward the score. It is not machinery;
it is the shape a built world presents to the scorer. It earns no file of its own and no
jargon ("contract" retired): it is the input format these functions expect.

The four functions are the whole grading shop:
  - oracle(world)      -> best-possible play: the ceiling (mechanical, deterministic).
  - floor(world)       -> lazy / no-skill play: the bottom.
  - score_run(...)     -> place a player's actual result in the floor->oracle band (LOOP 1).
  - grade_world(world) -> rate difficulty: is the best/lazy gap wide AND the top reachable
                          in budget (LOOP 2's smith). The scorer pointed at a world, not a run.

The engine underneath is a cost-weighted belief-MDP over the world's hidden-answer set: it
plans probes by how they split that set, and scores by how many scorable positions the
surviving answers all agree on (a position is *pinned* when its value is forced). It is a
dumb deterministic function of `(structure, observations)` -- never an LLM, and it never
looks inside a hypothesis, so it is world-agnostic. The "what a position is worth" law lives
in the *world* (`observe`), not here; that split is what keeps the grader generic and the
content swappable.

Per the integrity floor this module is model-free: it must never import hta.llm.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, Hashable, Mapping, Protocol, Sequence, Tuple


class World(Protocol):
    """The questions every world answers so the grader needs no per-world special-casing.

    A *built* world (a validated spec expanded by hta.world.spec.build) implements this. The
    grader reads only these; it never sees the world's internals. Positions are referred to by
    their index in `positions()` order -- that index is the `col` a run logs and submits.
    """

    budget: int

    def hypotheses(self) -> Sequence[Hashable]:
        """The enumerated space of possible hidden answers (one is the drawn truth)."""
        ...

    def positions(self) -> Sequence[object]:
        """Every position the grader reasons over, in a fixed order (probeable or scored)."""
        ...

    def cost(self, position: object) -> int:
        """What it costs to probe `position` (the budget is the scarce resource)."""
        ...

    def observe(self, position: object, hypothesis: Hashable) -> int:
        """What probing `position` reveals if `hypothesis` were the truth -- the world's value
        law (a lookup, never a solve). Hidden-state-bearing: only the harness holds a built
        world; this is never exposed on a player's tool surface (see hta/dgmh/play/server.py)."""
        ...

    def probeable(self, position: object) -> bool:
        """Whether a player may probe this position (probing it refines belief)."""
        ...

    def scored(self, position: object) -> bool:
        """Whether pinning this position counts toward coverage (the score)."""
        ...


# ---------------------------------------------------------------------------
# The world-agnostic belief engine. Every function below operates ONLY on a tableau
# (rows = hypotheses, cols = positions) + the cost vector + the two index sets. It never
# looks inside a hypothesis, so it rides any world unchanged.
# ---------------------------------------------------------------------------
def _tableau(world: World) -> Tuple[tuple, tuple, tuple, tuple]:
    """Expand a built world into the hashable tableau the engine plans over:
    (table, costs, scored_cols, probe_cols). `table[h][c]` is what position c reveals under
    hypothesis h -- the world's `observe` law, evaluated once. Hashable so the engine caches."""
    hyps = list(world.hypotheses())
    pos = list(world.positions())
    table = tuple(tuple(world.observe(p, h) for p in pos) for h in hyps)
    costs = tuple(int(world.cost(p)) for p in pos)
    scored_cols = tuple(i for i, p in enumerate(pos) if world.scored(p))
    probe_cols = tuple(i for i, p in enumerate(pos) if world.probeable(p))
    return table, costs, scored_cols, probe_cols


def _determined(table: tuple, scored_cols: tuple, H: frozenset) -> int:
    """How many scored positions are LOGICALLY pinned given the consistent hypothesis set H --
    i.e. every surviving hypothesis agrees on them. The dumb deterministic coverage measure."""
    if not H:
        return 0
    rep = next(iter(H))
    count = 0
    for c in scored_cols:
        v = table[rep][c]
        if all(table[h][c] == v for h in H):
            count += 1
    return count


def _partition(table: tuple, H: frozenset, c: int) -> Dict[int, frozenset]:
    """Probing position c splits H by the observed value (a deterministic observation -> a
    refinement of belief). Which branch the player lands in depends on the hidden truth."""
    groups: Dict[int, list] = {}
    for h in H:
        groups.setdefault(table[h][c], []).append(h)
    return {v: frozenset(hs) for v, hs in groups.items()}


@lru_cache(maxsize=None)
def _oracle(table: tuple, costs: tuple, scored_cols: tuple, probe_cols: tuple,
            budget: int) -> float:
    """Expected scored positions pinned by the optimal adaptive policy under the cost budget --
    exact value iteration over belief states. The ceiling. Cached on the (hashable) tableau so
    a world's reference is computed once and reused across every run it scores."""

    @lru_cache(maxsize=None)
    def V(H: frozenset, b: int) -> float:
        best = float(_determined(table, scored_cols, H))      # "stop and submit" value
        for c in probe_cols:
            if costs[c] > b:
                continue
            groups = _partition(table, H, c)
            if len(groups) == 1:
                continue                                       # non-informative -> never optimal
            exp = sum(len(g) / len(H) * V(g, b - costs[c]) for g in groups.values())
            if exp > best:
                best = exp
        return best

    return V(frozenset(range(len(table))), budget)


@lru_cache(maxsize=None)
def _floor(costs: tuple, scored_cols: tuple, probe_cols: tuple, budget: int) -> float:
    """No-inference baseline: pins only the scored positions it directly probes (never reads
    structure to predict the unseen), spending the budget on the cheapest such positions. The
    bottom of the band -- it proves that *allocation/inference*, not raw probing, does the work."""
    walkable = sorted(costs[i] for i in set(scored_cols) & set(probe_cols))
    spent = n = 0
    for c in walkable:
        if spent + c > budget:
            break
        spent += c
        n += 1
    return float(n)


def normalize(raw: float, floor: float, oracle: float) -> float:
    """Map a raw coverage count into the floor->oracle band, clipped to [0, 1]."""
    band = oracle - floor
    if band <= 1e-9:
        return 0.0
    return max(0.0, min(1.0, (raw - floor) / band))


# ---------------------------------------------------------------------------
# The four public functions: the World adapter on top of the engine.
# ---------------------------------------------------------------------------
def oracle(world: World) -> float:
    """Best-possible expected score under perfect adaptive play. The ceiling."""
    table, costs, scored_cols, probe_cols = _tableau(world)
    return _oracle(table, costs, scored_cols, probe_cols, int(world.budget))


def floor(world: World) -> float:
    """Lazy / no-skill baseline. The bottom of the band."""
    table, costs, scored_cols, probe_cols = _tableau(world)
    return _floor(costs, scored_cols, probe_cols, int(world.budget))


def score_run(world: World, run: Mapping) -> float:
    """Place a player's actual result in the floor->oracle band: 0 = lazy, 1 = oracle.

    `run` is the conduct the harness records, by position index (`col`):
      {"observations": [(col, value), ...],   # what the player probed and saw
       "submission":   {col: value, ...}}      # the answer it claims to know

    Coverage credit is capped to scored positions the player's own probes logically pin AND it
    submitted correctly -- so a lucky guess on an un-probed, un-pinned position scores nothing
    (the judge is ungameable), while a pinned position is forced and so comes for free.
    """
    table, costs, scored_cols, probe_cols = _tableau(world)
    H = frozenset(range(len(table)))
    for col, value in run.get("observations", ()):
        H = frozenset(h for h in H if table[h][int(col)] == value)
    submission = {int(k): v for k, v in (run.get("submission") or {}).items()}
    raw = 0
    if H and submission:
        rep = next(iter(H))
        for c in scored_cols:
            v = table[rep][c]
            if submission.get(c) == v and all(table[h][c] == v for h in H):
                raw += 1
    return normalize(raw, _floor(costs, scored_cols, probe_cols, int(world.budget)),
                     _oracle(table, costs, scored_cols, probe_cols, int(world.budget)))


def grade_world(world: World, cfg=None) -> dict:
    """Rate a world's difficulty for the smith: best/lazy gap + solvable-in-budget.

    Measures only; the gym's ship-gate decides. `hard` = the gap clears `world_gap_min` (skill
    matters); `solvable` = the oracle pins a `world_reach_min` fraction of the scorable positions
    (the budget buys real ground). Thresholds live in config, surfaced not hardcoded.

    (A richer hardness check -- the oracle must also beat a greedy/bounded planner, not just the
    lazy floor, so "hard" means taste and not a cheap formula -- is the ship-gate's next addition
    when LOOP 2 is wired; this is the band-level starting verdict.)
    """
    from hta.config import Config
    cfg = cfg or Config()
    table, costs, scored_cols, probe_cols = _tableau(world)
    B = int(world.budget)
    fl = _floor(costs, scored_cols, probe_cols, B)
    orc = _oracle(table, costs, scored_cols, probe_cols, B)
    scorable = len(scored_cols)
    gap = orc - fl
    reachable = orc / scorable if scorable else 0.0
    return {"floor": round(fl, 4), "oracle": round(orc, 4), "scorable": scorable,
            "gap": round(gap, 4), "reachable": round(reachable, 4),
            "hard": gap >= cfg.world_gap_min, "solvable": reachable >= cfg.world_reach_min}
