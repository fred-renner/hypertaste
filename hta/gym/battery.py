"""The dumb-player battery -- a model-free policy simulator that brackets a world.

Before a world may ship, we ask: is there room for *taste* in it, or does a dumb rule already
nearly max it? The battery answers by playing a handful of scripted strategies against the world
and reporting how each lands in the frozen floor->oracle band. It rides ONLY the generic `World`
interface (hypotheses / positions / cost / observe / probeable / scored) -- the same shape the
grader reads -- so it is world-agnostic and exact.

Two tiers of players:
  * **Naive members** (`greedy`, `random`, `sweep`, `lookahead2`) -- blind policies over the raw
    World. Best-possible play must clearly beat all of them, or the world has nothing to teach.
  * **ZPD stand-ins** (`champion`, `fix`) -- two GRAMMAR-AWARE policies (they read the built
    world's structural roles: which columns are gates, the payoff's prerequisite path). The
    *champion* analogue grabs immediate coverage and never scouts a gate; the *fix* scouts the
    prerequisite path step by step, then lets the gated payoff fall out. The gap between them is
    *room for taste* in the world's geometry.

THE HONEST BOUNDARY (see findings/2026-06-18-world-building-substrate.md): there is no live agent
in this pass, so the battery does NOT measure true ZPD -- that is defined against a specific agent
and only LOOP 1 can certify it. These scripted policies *bracket* the world: greedy is a floor on
the naive move, scout-then-read a witness that a skilled move reaches the band. A gap is a
*necessary* condition for ZPD (no gap -> definitely nothing to learn, reject cheaply), never a
measurement of it.

This is a GATE and a DIAGNOSTIC, never a number the smith grows: tuning a world to "beat greedy by
as much as possible" would just breed worlds specialised against greedy. The smith never sees it.
Model-free -- it must never import hta.llm.
"""

from __future__ import annotations

import random
from functools import lru_cache
from typing import Callable, Dict, Tuple

from hta.lab.scoring import World, floor, normalize, oracle


# ---------------------------------------------------------------------------
# The tableau the policies plan over (rows = hypotheses, cols = positions), built once per world.
# Mirrors hta.lab.scoring._tableau but kept here so the battery owns its own read of the World and
# the grader's internals stay private.
# ---------------------------------------------------------------------------
def _tableau(world: World):
    hyps = list(world.hypotheses())
    pos = list(world.positions())
    table = tuple(tuple(world.observe(p, h) for p in pos) for h in hyps)
    costs = tuple(int(world.cost(p)) for p in pos)
    scored_cols = tuple(i for i, p in enumerate(pos) if world.scored(p))
    probe_cols = tuple(i for i, p in enumerate(pos) if world.probeable(p))
    return table, costs, scored_cols, probe_cols


def _determined(table, scored_cols, H: frozenset) -> int:
    """Scored columns every surviving hypothesis agrees on -- the dumb coverage measure."""
    if not H:
        return 0
    rep = next(iter(H))
    return sum(1 for c in scored_cols
               if all(table[h][c] == table[rep][c] for h in H))


def _partition(table, H: frozenset, c: int) -> Dict[int, frozenset]:
    groups: Dict[int, list] = {}
    for h in H:
        groups.setdefault(table[h][c], []).append(h)
    return {v: frozenset(hs) for v, hs in groups.items()}


def _pinned(table, H: frozenset, col):
    """The value all surviving hypotheses agree on at `col`, or None if they still disagree."""
    if col is None:
        return None
    rep = next(iter(H))
    v = table[rep][col]
    return v if all(table[h][col] == v for h in H) else None


def simulate(world: World, pick: Callable) -> float:
    """Run a scripted `pick` policy against every hypothesis-as-truth and average the scored cells it
    logically pins. Blind: the policy sees only its refined belief `H` and the remaining budget (the
    same footing as the oracle), so the result is exactly what the policy can pin by playing."""
    table, costs, scored_cols, probe_cols = _tableau(world)
    B = int(world.budget)
    total = 0.0
    for hstar in range(len(table)):
        H = frozenset(range(len(table)))
        probed: set = set()
        b = B
        while True:
            c = pick(table, scored_cols, probe_cols, costs, H, probed, b)
            if c is None or costs[c] > b:
                break
            probed.add(c)
            b -= costs[c]
            v = table[hstar][c]
            H = frozenset(g for g in H if table[g][c] == v)
        total += _determined(table, scored_cols, H)
    return total / len(table)


# ---------------------------------------------------------------------------
# Naive members -- blind policies over the raw tableau. Each is
# `pick(table, scored, probe, costs, H, probed, b) -> col|None`.
# ---------------------------------------------------------------------------
def greedy(table, scored, probe, costs, H, probed, b):
    """Grab the affordable probe with the largest expected immediate coverage gain per unit cost.
    Stops when nothing pays *now* -- so it takes the bait and never scouts a gate (a gate read pins
    no scored cell on its own). This is also the champion ZPD stand-in."""
    base = _determined(table, scored, H)
    best_c, best = None, 0.0
    for c in probe:
        if c in probed or costs[c] > b:
            continue
        groups = _partition(table, H, c)
        if len(groups) == 1:
            continue
        exp = sum(len(g) / len(H) * _determined(table, scored, g) for g in groups.values())
        gain = (exp - base) / costs[c]
        if gain > best:
            best_c, best = c, gain
    return best_c


def make_random(seed: int = 0) -> Callable:
    """A fixed-seed random walker: probe a uniformly-random affordable, informative, un-probed cell.
    Seeded so the battery stays deterministic and reproducible."""
    rng = random.Random(seed)

    def pick(table, scored, probe, costs, H, probed, b):
        opts = [c for c in probe if c not in probed and costs[c] <= b
                and len(_partition(table, H, c)) > 1]
        return rng.choice(opts) if opts else None
    return pick


def sweep(table, scored, probe, costs, H, probed, b):
    """Systematically probe every affordable, informative cell in column order -- the exhaustive
    no-priorities baseline (it reads bait and gates alike, blind to which earns the payoff)."""
    for c in probe:
        if c not in probed and costs[c] <= b and len(_partition(table, H, c)) > 1:
            return c
    return None


@lru_cache(maxsize=None)
def _la_value(table, costs, scored, probe, H: frozenset, t: int, bud: int) -> float:
    """Best determined-cells reachable from belief `H` with `t` moves of lookahead under budget
    `bud` -- a truncated belief-MDP. Cached on the (hashable) tableau so the value function is
    computed once per world and reused across every move and every playout (the cache also persists
    across worlds; keys differ by tableau, so it is correct, just unbounded -- fine for a gym run)."""
    best = float(_determined(table, scored, H))
    if t == 0:
        return best
    for c in probe:
        if costs[c] > bud:
            continue
        groups = _partition(table, H, c)
        if len(groups) == 1:
            continue
        exp = sum(len(g) / len(H) * _la_value(table, costs, scored, probe, g, t - 1, bud - costs[c])
                  for g in groups.values())
        if exp > best:
            best = exp
    return best


def make_lookahead(depth: int = 2) -> Callable:
    """A bounded-lookahead planner: at each move play the probe that is optimal assuming only `depth`
    more moves (a truncated belief-MDP), then re-plan. depth=2 is the proven stronger bar -- a world
    is only 'hard' if best-play beats it, i.e. the payoff sits deeper than the planner can see."""
    def pick(table, scored, probe, costs, H, probed, b):
        best_c, best = None, -1.0
        for c in probe:
            if c in probed or costs[c] > b:
                continue
            groups = _partition(table, H, c)
            if len(groups) == 1:
                continue
            exp = sum(len(g) / len(H) * _la_value(table, costs, scored, probe, g, depth - 1,
                                                  b - costs[c])
                      for g in groups.values())
            if exp > best:
                best_c, best = c, exp
        return best_c
    return pick


def naive_members() -> Dict[str, Callable]:
    """The blind battery, built fresh per call so the (stateful, seeded) `random` walker restarts
    from the same seed every time -- the whole battery is reproducible run-to-run."""
    return {
        "greedy": greedy,
        "random": make_random(0),
        "sweep": sweep,
        "lookahead2": make_lookahead(2),
    }


# ---------------------------------------------------------------------------
# ZPD stand-ins -- GRAMMAR-AWARE policies. They take the built world (its structural roles) and
# return a blind `pick`. The champion grabs coverage and never scouts; the fix scouts the
# prerequisite path step by step, then mops up bait once the payoff has fallen out.
# ---------------------------------------------------------------------------
def champion_pick(world) -> Callable:
    """The CHAMPION analogue: greedy immediate coverage, never scouts a gate. Identical to the naive
    `greedy` (a gate pays zero now, so greedy never reads one) -- named separately because it is the
    rule the world must break, the lower edge of the ZPD bracket."""
    return greedy


def _walk_pick(world) -> Callable:
    """Scout the prerequisite path directly: read the start variable, let its pinned value name the
    next variable on the walk, read that, ... to the final variable -- at which point the gated
    payoff is logically pinned -- then mop up bait. The robust move when the budget is tight (no slack
    to spend on anything but the path)."""
    def pick(table, scored, probe, costs, H, probed, b):
        r = world.path_start
        for hop in (*world.path_hops, None):       # None marks the final variable (no further hop)
            col = world.gate_col[r]
            v = _pinned(table, H, col)
            if v is None:                          # this prerequisite not yet scouted -> read it
                if col not in probed and costs[col] <= b:
                    return col
                break                              # can't afford the scout -> fall through to mop-up
            if hop is None:                        # final variable pinned -> the payoff is earned
                break
            r = hop[v % world.K]
        for col in world.bait_cols:                # path done (or stalled): take the immediate bait
            if col not in probed and costs[col] <= b:
                return col
        return None
    return pick


def _leaf_pick(world) -> Callable:
    """Scout, but exploit agreement: the payoff mirrors whichever of the prerequisite path's TWO
    final candidates the walk selects, so PEEK at both first -- cheap; if they already agree the
    payoff is pinned no matter which is selected, so STOP and bank bait. Only on disagreement do you
    pay to scout the path. The move a rigid 'always walk the whole path' scout misses -- it is exactly
    the slack the oracle banks on deeper worlds -- so it tracks the ceiling when the budget is loose
    enough to afford the worst-case recovery."""
    finals = tuple(world.path_hops[-1])

    def pick(table, scored, probe, costs, H, probed, b):
        for v in finals:                           # (1) peek the two candidate payoff sources
            col = world.gate_col[v]
            if _pinned(table, H, col) is None and col not in probed and costs[col] <= b:
                return col
        vals = [_pinned(table, H, world.gate_col[v]) for v in finals]
        agree = vals and all(x is not None and x == vals[0] for x in vals)
        if not agree:                              # (2) candidates differ -> scout to learn which is live
            r = world.path_start
            for hop in world.path_hops:
                col = world.gate_col[r]
                v = _pinned(table, H, col)
                if v is None:
                    if col not in probed and costs[col] <= b:
                        return col
                    break
                r = hop[v % world.K]
        for col in world.bait_cols:                # (3) payoff earned (or stalled) -> take the bait
            if col not in probed and costs[col] <= b:
                return col
        return None
    return pick


def fix_pick(world) -> Callable:
    """The FIX analogue: the tasteful, articulable move that earns the gated payoff -- the upper edge
    of the ZPD bracket, a witness that a skilled disposition reaches the band. Reads only the built
    world's structural roles (`gate_col`, `path_start`, `path_hops`).

    It selects its tactic by the scarcity regime (a single budget-vs-depth read, the kind of position
    assessment taste IS): with slack to spare (`budget >= depth + 1`) peek the two payoff candidates
    and bank bait when they agree; under a tight budget scout the path directly, with no reads to
    waste on a peek it cannot recover from. Either way it tracks the oracle in its regime, so 'is
    this world solvable by a skilled move?' gets an honest yes/no, not an artifact of a rigid script."""
    depth = 1 + len(world.path_hops)               # variables pinned on any walk
    return _leaf_pick(world) if world.budget >= depth + 1 else _walk_pick(world)


# ---------------------------------------------------------------------------
# The report: every player's place in the floor->oracle band, plus the brackets the ship-gate reads.
# ---------------------------------------------------------------------------
def battery_report(world) -> dict:
    """Play the whole battery against `world` and place each member in the frozen band.

    Returns raw (mean scored cells pinned) and normalized (0 = lazy floor, 1 = oracle) scores for
    every naive member and the two ZPD stand-ins, plus:
      - `best_naive` / `best_naive_norm`: the strongest blind player (best-play must beat it);
      - `champion_norm` / `fix_norm`: the ZPD bracket the ship-gate gates on.
    """
    fl, orc = floor(world), oracle(world)

    def placed(pick) -> Tuple[float, float]:
        raw = simulate(world, pick)
        return raw, normalize(raw, fl, orc)

    naive = {name: placed(pick) for name, pick in naive_members().items()}
    champ_raw, champ_norm = placed(champion_pick(world))
    fix_raw, fix_norm = placed(fix_pick(world))

    best_name = max(naive, key=lambda n: naive[n][0])
    best_raw, best_norm = naive[best_name]
    return {
        "floor": fl, "oracle": orc,
        "naive": {n: {"raw": round(r, 4), "norm": round(z, 4)} for n, (r, z) in naive.items()},
        "best_naive": best_name, "best_naive_raw": round(best_raw, 4),
        "best_naive_norm": round(best_norm, 4),
        "champion_raw": round(champ_raw, 4), "champion_norm": round(champ_norm, 4),
        "fix_raw": round(fix_raw, 4), "fix_norm": round(fix_norm, 4),
    }
