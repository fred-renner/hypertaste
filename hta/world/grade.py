"""The grading engine — the integrity floor's dumb deterministic math (DESIGN.md §2). Model-free,
token-free, world-agnostic: everything here is `f(structure, observations)` over the enumerated
hypothesis set, never an LLM. The world-smith proposes only STRUCTURE; the referee (coverage), the
floor, and the perfect-play benchmark (the belief-MDP oracle) are all RE-DERIVED here, mechanically,
from that structure — which is what keeps a movable score out of the agent's reach.

It rides on `build_tableau(spec)` (hta/world/language.py) and never looks inside the parts:

  * **coverage** = cells LOGICALLY pinned by the consistent hypothesis set (`determined`). The dumb
    measure; a lucky guess on an un-probed cell pins nothing.
  * **floor** = a no-inference walker (probe the cheapest coverage cells you can afford); the baseline
    that proves *allocation*, not raw probing, is doing the work.
  * **oracle** = the optimal blind ADAPTIVE policy by exact value iteration over belief states under
    the cost budget. Computable on a small world (a finite belief tree), but NOT a shallow rule when
    the payoff is trail-deep — the threshold being cleared.
  * **screen** = the model-free verdict: the threshold gap (oracle vs the best articulable heuristic,
    incl. 2-step lookahead, normalized into the floor->oracle band) plus the anti-cliff ramp.

Scores are reported in the model-free **floor->oracle band**: 0 == the no-inference floor, 1 == the
optimal adaptive oracle. The references are spec-constant, so they are computed once and cached.
"""

from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from .language import WorldSpec, build_tableau


# ---------------------------------------------------------------------------
# Generic belief-set primitives.
# ---------------------------------------------------------------------------
def determined(table, cols: Tuple[int, ...], H: frozenset) -> int:
    """How many cells are LOGICALLY pinned given the consistent hypothesis set H — every surviving
    hypothesis agrees on them. The dumb deterministic coverage measure; no LLM."""
    if not H:
        return 0
    rep = next(iter(H))
    count = 0
    for c in cols:
        v = table[rep][c]
        if all(table[h][c] == v for h in H):
            count += 1
    return count


def _partition(table, H: frozenset, c: int) -> Dict[int, frozenset]:
    """Probing cell c splits H by the observed value (a deterministic refinement of the belief). The
    branch the agent lands in depends on the hidden true world."""
    groups: Dict[int, list] = {}
    for h in H:
        groups.setdefault(table[h][c], []).append(h)
    return {v: frozenset(hs) for v, hs in groups.items()}


def normalize(raw: float, floor: float, oracle: float) -> float:
    """Map a raw coverage count into the floor->oracle band, clipped to [0, 1]."""
    band = oracle - floor
    if band <= 1e-9:
        return 0.0
    return max(0.0, min(1.0, (raw - floor) / band))


# ---------------------------------------------------------------------------
# References (cached on the frozen, hashable spec).
# ---------------------------------------------------------------------------
@lru_cache(maxsize=None)
def floor_value(spec: WorldSpec) -> float:
    """No-inference walker: determines only the cells it directly probes, spending the cost budget on
    the cheapest cells that are both coverage and probeable."""
    _, _, costs, cov, probe = build_tableau(spec)
    walkable = sorted(costs[i] for i in set(cov) & set(probe))
    spent = n = 0
    for c in walkable:
        if spent + c > spec.budget:
            break
        spent += c
        n += 1
    return float(n)


@lru_cache(maxsize=None)
def oracle_value(spec: WorldSpec) -> float:
    """Expected cells determined by the optimal blind ADAPTIVE policy under the cost budget — exact
    value iteration over belief states. The belief-MDP is the costly part; cached per spec."""
    table, cells, costs, cov, probe = build_tableau(spec)
    H0 = frozenset(range(len(table)))

    @lru_cache(maxsize=None)
    def V(H: frozenset, b: int) -> float:
        best = float(determined(table, cov, H))             # "stop and submit" value
        for c in probe:
            if costs[c] > b:
                continue
            groups = _partition(table, H, c)
            if len(groups) == 1:
                continue                                    # non-informative -> never optimal
            exp = sum(len(g) / len(H) * V(g, b - costs[c]) for g in groups.values())
            if exp > best:
                best = exp
        return best

    return V(H0, spec.budget)


@lru_cache(maxsize=None)
def clairvoyant_value(spec: WorldSpec) -> float:
    """Omniscient ceiling: per true world, the best probe sequence chosen knowing that world. The
    belief-MDP <= clairvoyant; the gap is the price of uncertainty. Context only (not the reference)."""
    table, cells, costs, cov, probe = build_tableau(spec)
    H0 = frozenset(range(len(table)))
    total = 0.0
    for hstar in range(len(table)):
        @lru_cache(maxsize=None)
        def Vc(H: frozenset, b: int) -> float:
            best = float(determined(table, cov, H))
            for c in probe:
                if costs[c] > b:
                    continue
                groups = _partition(table, H, c)
                if len(groups) == 1:
                    continue
                cand = Vc(groups[table[hstar][c]], b - costs[c])
                if cand > best:
                    best = cand
            return best
        total += Vc(H0, spec.budget)
    return total / len(table)


# ---------------------------------------------------------------------------
# The articulable basket: closed-form blind adaptive policies a hand spec (Opus, from outside) could
# write. If the best of these matches the oracle, the optimal policy IS articulable -> below
# threshold. Each is `pick(table, cov, probe, costs, H, probed, b) -> col|None`.
# ---------------------------------------------------------------------------
def simulate(spec: WorldSpec, pick) -> float:
    """Run an articulable policy against every true world, averaging determined cells. Blind (it sees
    only its own belief and the cost budget), same footing as the oracle — so the gap is exactly the
    non-articulable residue."""
    table, cells, costs, cov, probe = build_tableau(spec)
    total = 0.0
    for hstar in range(len(table)):
        H = frozenset(range(len(table)))
        probed: set = set()
        b = spec.budget
        while True:
            c = pick(table, cov, probe, costs, H, probed, b)
            if c is None or costs[c] > b:
                break
            probed.add(c)
            b -= costs[c]
            v = table[hstar][c]
            H = frozenset(g for g in H if table[g][c] == v)
        total += determined(table, cov, H)
    return total / len(table)


def _greedy_info(table, cov, probe, costs, H, probed, b):
    """Probe the affordable cell with the most expected belief-refinement per unit cost."""
    best_c, best = None, None
    for c in probe:
        if c in probed or costs[c] > b:
            continue
        groups = _partition(table, H, c)
        if len(groups) == 1:
            continue
        score = -sum(len(g) ** 2 for g in groups.values()) / costs[c]
        if best is None or score > best:
            best_c, best = c, score
    return best_c


def _greedy_determined(table, cov, probe, costs, H, probed, b):
    """Probe the affordable cell with the largest expected immediate determined-gain per unit cost —
    the myopic knapsack instinct. It grabs the clearing blocks and never starts a trail (signpost
    reads pay zero coverage, so they never top the ranking)."""
    base = determined(table, cov, H)
    best_c, best = None, None
    for c in probe:
        if c in probed or costs[c] > b:
            continue
        groups = _partition(table, H, c)
        if len(groups) == 1:
            continue
        exp = sum(len(g) / len(H) * determined(table, cov, g) for g in groups.values())
        gain = (exp - base) / costs[c]
        if best is None or gain > best:
            best_c, best = c, gain
    return best_c


BASKET = {"greedy_info": _greedy_info, "greedy_determined": _greedy_determined}


def lookahead_value(spec: WorldSpec, depth: int) -> float:
    """The strongest *articulable* policy: a bounded-lookahead planner. At each move it plays the
    probe optimal assuming only `depth` more moves (a truncated belief-MDP), then re-plans. The
    verdict 'above threshold' is robust iff the full oracle still beats depth=2 — i.e. the optimal
    policy needs deeper-than-bounded planning, not a weak basket."""
    table, cells, costs, cov, probe = build_tableau(spec)

    @lru_cache(maxsize=None)
    def V(H: frozenset, t: int, b: int) -> float:
        best = float(determined(table, cov, H))
        if t == 0:
            return best
        for c in probe:
            if costs[c] > b:
                continue
            groups = _partition(table, H, c)
            if len(groups) == 1:
                continue
            exp = sum(len(g) / len(H) * V(g, t - 1, b - costs[c]) for g in groups.values())
            if exp > best:
                best = exp
        return best

    total = 0.0
    for hstar in range(len(table)):
        H = frozenset(range(len(table)))
        probed: set = set()
        b = spec.budget
        while True:
            best_c, best = None, None
            for c in probe:
                if c in probed or costs[c] > b:
                    continue
                groups = _partition(table, H, c)
                if len(groups) == 1:
                    continue
                exp = sum(len(g) / len(H) * V(g, depth - 1, b - costs[c]) for g in groups.values())
                if best is None or exp > best:
                    best_c, best = c, exp
            if best_c is None:
                break
            probed.add(best_c)
            b -= costs[best_c]
            v = table[hstar][best_c]
            H = frozenset(g for g in H if table[g][best_c] == v)
        total += determined(table, cov, H)
    return total / len(table)


def _linearity_r2(curve: List[float]) -> float:
    """R^2 of `curve` against the straight line 0..1. ~1.0 => clean ramp."""
    G = len(curve) - 1
    line = [f / G for f in range(G + 1)]
    mean = sum(curve) / len(curve)
    ss_tot = sum((y - mean) ** 2 for y in curve)
    ss_res = sum((y - l) ** 2 for y, l in zip(curve, line))
    return 1.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot


# ---------------------------------------------------------------------------
# The full model-free verdict.
# ---------------------------------------------------------------------------
def screen(spec: WorldSpec, clair: bool = True) -> dict:
    """Threshold gap (oracle vs best articulable heuristic incl. 2-step lookahead, normalized into the
    floor->oracle band) plus the ramp shape. `clair=False` skips the omniscient ceiling (a per-world
    DP, the costly part) when sweeping many specs."""
    floor = floor_value(spec)
    oracle = oracle_value(spec)
    clairvoyant = clairvoyant_value(spec) if clair else float("nan")
    heurs = {name: simulate(spec, pick) for name, pick in BASKET.items()}
    heurs["lookahead2"] = lookahead_value(spec, depth=2)
    best_heur = max(heurs.values())
    band = oracle - floor
    gap_norm = (oracle - best_heur) / band if band > 1e-9 else 0.0
    heur_norm = (best_heur - floor) / band if band > 1e-9 else 0.0
    curve = spec.ramp_curve()
    steps = [b - a for a, b in zip(curve, curve[1:])]
    return {
        "name": spec.name, "R": spec.R, "K": spec.K, "M": spec.M,
        "n_hyps": spec.K ** spec.R, "budget": spec.budget,
        "Lv": sum(f.Lv for f in spec.forks()),
        "floor": floor, "best_heur": best_heur, "oracle": oracle, "clairvoyant": clairvoyant,
        "heurs": heurs, "gap_raw": oracle - best_heur, "gap_norm": gap_norm,
        "heur_norm": heur_norm, "ramp_r2": _linearity_r2(curve),
        "ramp_maxstep": max(steps) if steps else 0.0,
        "ramp_monotone": all(s > -1e-9 for s in steps),
    }


# ---------------------------------------------------------------------------
# The dumb scorer (the judge), as a pure function of the probe LOG and the submitted map. The same
# `determined` the oracle/floor use; capped to cells the agent's OWN probes logically pin, then
# band-normalized. Never an LLM, never the player's word for it.
# ---------------------------------------------------------------------------
def observed_belief(table, log: List[dict]) -> frozenset:
    """The hypothesis set consistent with every observation in the log — the agent's realized belief."""
    H = frozenset(range(len(table)))
    for e in log:
        col, val = e["col"], e["value"]
        H = frozenset(h for h in H if table[h][col] == val)
    return H


def coverage_earned(spec: WorldSpec, log: List[dict], submitted: Optional[Dict[int, int]]) -> int:
    """Cells the agent EARNED: coverage cells its probes logically pin AND it submitted correctly.
    Capping to pinned cells makes the judge ungameable (a lucky guess on an un-probed cell scores
    zero); a pinned cell's value is forced, so a competent agent gets it for free. No submission ->
    nothing earned (a legitimate worst score)."""
    if not submitted:
        return 0
    table, cells, costs, cov, probe = build_tableau(spec)
    H = observed_belief(table, log)
    if not H:
        return 0
    rep = next(iter(H))
    n = 0
    for c in cov:
        v = table[rep][c]
        if all(table[h][c] == v for h in H) and submitted.get(c) == v:
            n += 1
    return n


def score_submission(spec: WorldSpec, log: List[dict], submitted: Optional[Dict[int, int]],
                     used: int = 0) -> dict:
    """Band-normalized coverage: raw earned cells mapped into the model-free floor->oracle band."""
    raw = coverage_earned(spec, log, submitted)
    floor = floor_value(spec)
    oracle = oracle_value(spec)
    table, _, _, cov, _ = build_tableau(spec)
    return {"raw": raw, "floor": round(floor, 4), "oracle": round(oracle, 4),
            "norm": round(normalize(raw, floor, oracle), 4),
            "determined": int(determined(table, cov, observed_belief(table, log))),
            "used": used, "budget": spec.budget}
