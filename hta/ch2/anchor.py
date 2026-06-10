"""The Chapter-2 **anchor family** — the B2-allocation world (RESET_DESIGN.md -> "The world
design"). Where `threshold.py`'s register world makes *inference* hard (a coupled joint-solve
over GF(K) — which is exactly why Opus could write a brute-force solver and lift it to 100%),
this world makes inference **trivial** and *allocation* hard. Reconstruction given the probes is
a pure lookup; the only hard thing is deciding **which** probes to spend, under a punishing
budget, deception, variable cost, and a payoff that only materializes deep in a trail.

The mechanism is **indirection, not coupling.** A *trail*:

    trailhead register --(its value points to)-->  a waypoint register
    waypoint register  --(its value points to)-->  the LANDMARK register
    the landmark register's value generates a big VALLEY block  (Lv cells, the deep payoff)

To cover the valley you must read the trailhead, follow it to the waypoint, follow that to the
landmark, then read the landmark — a **depth-3** trail. Every step is a *lookup* (the pointer maps are public; the
register *values* are the hidden seed), never a solve, so the reconstruction stays B2. But the
value of the trail is non-submodular and **deep**: the map probe pays zero valley cells, the waypoint
probe pays zero, the landmark probe pays zero — until all three land and the whole valley flips on at
once. So:

  * **greedy-determined** chases the immediate-coverage clearing (each register's small direct block
    pays `Ld` cells now) and never starts the trail (it pays nothing now);
  * **greedy-info** chases entropy, not the landmark;
  * a **2-step lookahead** planner cannot see past the waypoint to the payoff (it is 3 probes away),
    so it will not even take the first step.

Only the full belief-MDP oracle (planning to the budget horizon) takes the boring door. That is
the same "deep commitment beats bounded planning" gap that put `trap-tetra` above threshold —
but reached by **allocation depth**, not inference depth. The contrast with `threshold.py` is the
whole point of the reset: this gap survives an English playbook (you cannot brute-force a trail
search in prose), and its *content* — which register the realized trail ends on — is learnable
only by playing this instance, never derivable from the public structure.

The anchor virtues ride on this core (RESET_DESIGN.md): **allocation under scarcity** (budget <<
the probeable blocks, so you cannot try everything), **deception** (the clearing blocks pay now; the
trail pays nothing until the end), **emergent opportunity** (the landmark's identity surfaces only as
you walk the trail), and **variable cost** (`cost_signpost`/`cost_clearing`; the budget is a *cost* budget,
so value-of-information is cost-weighted — and a costlier clearing widens the gap, see `run_anchor.py`).
The fifth battery virtue, **calibrated commitment**, is the tiny-budget regime where the oracle
must bet on a partial trail; **late disconfirmation** is a *trajectory/memory* pressure (a thread
that looks rich until a late probe retracts it) that shapes the live student's revision rather than
the model-free oracle gap — so it lives in the realized world for calibration, not in this screen.

Everything is a dumb deterministic `f(structure, observations)` over an enumerated hypothesis set
(K**R register assignments) — the integrity-floor coverage judge, no LLM. The oracle
is exact and token-free (a finite belief tree), so the reference stays computable; it is just no
longer *expressible* as a shallow rule.
"""

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from math import comb
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Generic belief-set helpers (table-agnostic) and the ramp-quality metric. These are the
# dumb-deterministic primitives the oracle/heuristics/screen are built from — no LLM.
# ---------------------------------------------------------------------------
def determined(table, cols: Tuple[int, ...], H: frozenset) -> int:
    """How many cells are LOGICALLY pinned given the consistent hypothesis set H — i.e. every
    surviving hypothesis agrees on them. The dumb deterministic coverage measure; no LLM."""
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
    """Probing cell c splits H by the observed value (deterministic observation -> a refinement
    of the belief). The branch the agent lands in depends on the hidden true world."""
    groups: Dict[int, list] = {}
    for h in H:
        groups.setdefault(table[h][c], []).append(h)
    return {v: frozenset(hs) for v, hs in groups.items()}


def linearity_r2(curve: List[float]) -> float:
    """R^2 of `curve` against the straight line 0..1 over its index range. ~1.0 => clean ramp."""
    G = len(curve) - 1
    line = [f / G for f in range(G + 1)]
    mean = sum(curve) / len(curve)
    ss_tot = sum((y - mean) ** 2 for y in curve)
    ss_res = sum((y - l) ** 2 for y, l in zip(curve, line))
    return 1.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot


@dataclass(frozen=True)
class TrailSpec:
    """A B2 trail world. The layout (which registers are signposts, the public pointer tables, the
    block lengths, the costs) is known to everyone; the hidden seed is the K**R register
    assignment, which is what fixes where the realized trail ends. Two register roles, and the
    split is the whole gap:

      * **signpost** registers (`signposts`, incl. `trailhead`) are read through a cheap length-`Ls`
        cell that pays almost nothing in coverage — pure pointers. The trail walks them.
      * **clearing** registers (everything else) carry a fat direct block of length `Ld` — a big
        *immediate* coverage payoff for one probe. They are NOT on the trail; they are the bait.

    `waypoints`/`landmarks` are the public pointer **tree**: `trailhead`'s value picks a waypoint register
    (`waypoints[r_trailhead]`), the waypoint's value picks the landmark register (`landmarks[branch][r_waypoint]`) — two
    hops, so the landmark is **depth-3** from the start (trailhead, waypoint, landmark). Walking the trail pays ~0
    per step until all three signposts land and the valley (`Lv` cells) flips on at once; a greedy
    or 2-step planner takes the clearings instead and never reaches it."""
    name: str
    R: int                                  # variables (hidden values -> K**R hypotheses, small)
    K: int                                  # values per variable
    Ld: int                                 # clearing direct-block length (the immediate-coverage bait)
    Lv: int                                 # valley length (the deep, trail-gated payoff — the prize)
    trailhead: int                               # the map register (entry of the trail)
    waypoints: Tuple[int, ...]                 # length K: waypoints[r_trailhead] picks the waypoint register
    landmarks: Tuple[Tuple[int, ...], ...]      # K x K: landmarks[branch][r_waypoint] picks the landmark register
    budget: int                             # scarce COST budget (probes draw from it, cost-weighted)
    Ls: int = 1                             # signpost cell length (kept tiny: a pointer, not payoff)
    cost_signpost: int = 1                       # cost to read a signpost (the cheap door)
    cost_clearing: int = 1                      # cost to probe a clearing block (variable-cost knob)

    def signposts(self) -> Tuple[int, ...]:
        """The trail registers, read as cheap pointers: trailhead + every waypoint + every reachable landmark.
        Auto-derived from the public tree so the layout and the cells stay in lockstep."""
        regs = {self.trailhead, *self.waypoints}
        regs.update(l for row in self.landmarks for l in row)
        return tuple(sorted(regs))

    def clearings(self) -> Tuple[int, ...]:
        sign = set(self.signposts())
        return tuple(i for i in range(self.R) if i not in sign)

    def landmark_reg(self, hyp: Tuple[int, ...]) -> int:
        """Walk the public trail under this hypothesis's values to the landmark: trailhead's value picks
        the waypoint branch, the waypoint's value picks the landmark. K x K fan-out, so the landmark pool cannot
        be brute-pinned inside a 2-step horizon — that is what forces the depth-3 commitment."""
        branch = hyp[self.trailhead] % self.K
        waypoint = self.waypoints[branch]
        return self.landmarks[branch][hyp[waypoint] % self.K]

    def trail_regs(self, hyp: Tuple[int, ...]) -> Tuple[int, ...]:
        """The registers the realized trail visits (trailhead, the waypoint, the landmark) — the set that must
        all be pinned before the valley flips on. Data-dependent: that is the hidden content."""
        branch = hyp[self.trailhead] % self.K
        waypoint = self.waypoints[branch]
        return tuple(dict.fromkeys((self.trailhead, waypoint, self.landmarks[branch][hyp[waypoint] % self.K])))

    def cells(self) -> List[Tuple]:
        """Column layout (descriptors; values are per-hypothesis): cheap signpost cells, fat clearing
        blocks, then the landmark valley."""
        cells: List[Tuple] = []
        for s in self.signposts():
            for p in range(self.Ls):
                cells.append(("sig", s, p))
        for i in self.clearings():
            for p in range(self.Ld):
                cells.append(("direct", i, p))
        for p in range(self.Lv):
            cells.append(("valley", p))
        return cells

    def cost_of(self, cell: Tuple) -> int:
        return self.cost_signpost if cell[0] == "sig" else self.cost_clearing

    @property
    def M(self) -> int:
        return len(self.cells())

    def world_map_public(self, remaining: int) -> dict:
        """The PUBLIC rules of the game (no hidden values), owned by the spec so a *richer* world
        describes itself through the **unchanged** episode airgap (`episode_state.world_map`
        delegates here): the link chain, the cell layout with costs/roles, and the deterministic
        value law. Exposing the law (not the values) is what makes reconstruction a reachable LOOKUP
        — the same law the oracle/heuristics compute under — without touching the band; what stays
        hidden is the ALLOCATION. The interface is generic (variable/value, cells/links/budget/
        coverage): no world-story leaks, so the player cannot overfit the container."""
        value_rule = (
            "Cell values are a deterministic lookup, never a pattern to guess: a cell's value = "
            "(its variable's hidden value + pos) mod K. A cell with a `var` field uses that "
            "variable; a cell marked mirrors='target' uses the TARGET variable — the one the public "
            "link chain resolves to under the hidden values (start at variable `root`, its value "
            "selects the next variable links.level1[value], that variable's value selects the target "
            "links.level2[branch][value]). So once your probes pin a variable's value, every cell "
            "keyed to that variable is fully determined — you reconstruct it, you do not guess it.")
        return {"R": self.R, "K": self.K, "budget": self.budget, "remaining": remaining,
                "value_rule": value_rule,
                "links": {"root": self.trailhead, "level1": list(self.waypoints),
                          "level2": [list(r) for r in self.landmarks]},
                "cells": public_cells(self)}

    def report_blurb(self) -> str:
        """One-line PUBLIC description for the sanitized meta/inventor report (no hidden values)."""
        return (f"a single chain of public links (root variable {self.trailhead} -> level1 "
                f"{list(self.waypoints)} -> level2 {[list(r) for r in self.landmarks]}) over "
                f"{self.R} variables; some cells only read link variables and pay ZERO coverage, "
                f"others pay immediately, and a deep block of cells pays only once the link chain is "
                f"walked end to end to its target variable")

    # ---- declarative (de)serialization (kind-tagged so the airgap can ride either spec) ----
    def to_dict(self) -> dict:
        return {"kind": "trail", "name": self.name, "R": self.R, "K": self.K, "Ld": self.Ld,
                "Lv": self.Lv, "trailhead": self.trailhead, "waypoints": list(self.waypoints),
                "landmarks": [list(r) for r in self.landmarks], "budget": self.budget, "Ls": self.Ls,
                "cost_signpost": self.cost_signpost, "cost_clearing": self.cost_clearing}

    @classmethod
    def from_dict(cls, d: dict) -> "TrailSpec":
        return cls(name=d["name"], R=d["R"], K=d["K"], Ld=d["Ld"], Lv=d["Lv"],
                   trailhead=d["trailhead"], waypoints=tuple(d["waypoints"]),
                   landmarks=tuple(tuple(r) for r in d["landmarks"]), budget=d["budget"],
                   Ls=d.get("Ls", 1), cost_signpost=d.get("cost_signpost", 1),
                   cost_clearing=d.get("cost_clearing", 1))


# ---------------------------------------------------------------------------
# The deterministic expander — generic over the spec *protocol* (`cells`, `cost_of`, `clearings`,
# `trail_regs`, `landmark_reg`, K/R/Ld/Lv/budget). TrailSpec implements it; so does ForkedTrailSpec
# (worlds.py). That genericity is the whole point: the world-smith evolves the world's STRUCTURE
# while the oracle/screen below are re-derived mechanically, never re-authored.
# ---------------------------------------------------------------------------
def public_cells(spec) -> List[dict]:
    """The cell layout as PUBLIC descriptors — no hidden values, no world-story. Each cell carries
    its cost, whether it is `probeable` / counts for `coverage`, and which `var` it reads (or
    `mirrors='target'` if its variable is the link-resolved target). The generic role falls out of
    those flags, so no narrative kind label is exposed. Shared by every spec's `world_map_public`."""
    out = []
    for i, c in enumerate(spec.cells()):
        entry = {"col": i, "cost": spec.cost_of(c),
                 "probeable": c[0] in ("sig", "direct"), "coverage": c[0] in ("direct", "valley")}
        if c[0] in ("sig", "direct"):
            entry["var"], entry["pos"] = c[1], c[2]
        else:
            entry["pos"], entry["mirrors"] = c[1], "target"
        out.append(entry)
    return out


def cell_value(spec, cell: Tuple, hyp: Tuple[int, ...]) -> int:
    """Deterministic expander, one cell, one hypothesis. Signpost/clearing: (r_i + p) — a lookup.
    Valley: mirror the LANDMARK register the trail resolves to under this hypothesis
    (`spec.landmark_reg`) — a lookup too, once the trail is walked. No cell is ever a joint-solve;
    that is the B2 line."""
    kind = cell[0]
    if kind in ("sig", "direct"):
        _, i, p = cell
        return (hyp[i] + p) % spec.K
    _, p = cell                             # valley
    return (hyp[spec.landmark_reg(hyp)] + p) % spec.K


def build_tableau(spec):
    """Rows = hypotheses (K**R register assignments); columns = cells; plus the cost vector and two
    index sets that are the whole design:

      * `probe_cols` — what an agent may actually *probe*: the signposts (clue reads) and the clearing
        blocks. The valley is NOT here — it is **inference-only**, the deep payoff you *reconstruct*
        by following the trail, never drill. (A single valley probe would otherwise read the landmark
        value and unlock the block in one move -> submodular, below threshold.)
      * `cov_cols` — what counts as *coverage*: the clearing blocks and the valley. Signposts are NOT
        here — they are instruments (the map's legend), not map cells. So walking the trail pays
        **zero coverage** until the valley flips on; no prefix of the trail pays, which is what
        makes the gap robust to a bounded planner (it can climb a trail whose every step pays +1;
        it cannot climb one whose steps pay 0 with the reward three probes away)."""
    cells = spec.cells()
    hyps = list(product(range(spec.K), repeat=spec.R))
    table = tuple(tuple(cell_value(spec, c, h) for c in cells) for h in hyps)
    costs = tuple(spec.cost_of(c) for c in cells)
    probe_cols = tuple(i for i, c in enumerate(cells) if c[0] in ("sig", "direct"))
    cov_cols = tuple(i for i, c in enumerate(cells) if c[0] in ("direct", "valley"))
    return table, cells, costs, cov_cols, probe_cols


# ---------------------------------------------------------------------------
# The cost-weighted belief-MDP oracle: the optimal ADAPTIVE policy by exact value iteration over
# belief states, spending a COST budget. Computable on a small world (finite belief tree, no LLM
# tokens) but NOT a shallow rule when the payoff is trail-deep — the threshold being cleared.
# ---------------------------------------------------------------------------
@lru_cache(maxsize=None)
def oracle_value(spec, budget: int = None) -> float:
    """Expected cells determined by the optimal blind adaptive policy under the cost budget. Cached
    on the (frozen, hashable) spec so a world's reference is computed once and reused across every
    episode it scores — the belief-MDP is the costly part."""
    B = spec.budget if budget is None else budget
    table, cells, costs, cov, probe = build_tableau(spec)
    H0 = frozenset(range(len(table)))

    @lru_cache(maxsize=None)
    def V(H: frozenset, b: int) -> float:
        best = float(determined(table, cov, H))        # "stop and submit" value
        for c in probe:
            if costs[c] > b:
                continue
            groups = _partition(table, H, c)
            if len(groups) == 1:
                continue                            # non-informative -> never optimal
            exp = sum(len(g) / len(H) * V(g, b - costs[c]) for g in groups.values())
            if exp > best:
                best = exp
        return best

    return V(H0, B)


def clairvoyant_value(spec: TrailSpec, budget: int = None) -> float:
    """Omniscient ceiling: per true world, the best probe sequence chosen knowing that world
    (observations are then deterministic — always the true branch). belief-MDP <= clairvoyant;
    the gap is the price of uncertainty. Context only — NOT the threshold reference."""
    B = spec.budget if budget is None else budget
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
                child = groups[table[hstar][c]]     # the agent already knows the world
                cand = Vc(child, b - costs[c])
                if cand > best:
                    best = cand
            return best
        total += Vc(H0, B)
    return total / len(table)


@lru_cache(maxsize=None)
def floor_value(spec, budget: int = None) -> float:
    """No-inference walker: determines only the cells it directly probes (never reads structure to
    predict the unseen), spending the cost budget on the cheapest cells. The dumb baseline that
    proves *inference/allocation*, not raw probing, is doing the work. Cached on the spec."""
    B = spec.budget if budget is None else budget
    _, _, costs, cov, probe = build_tableau(spec)
    walkable = sorted(costs[i] for i in set(cov) & set(probe))  # cells that are both coverage & probeable
    spent = n = 0
    for c in walkable:
        if spent + c > B:
            break
        spent += c
        n += 1
    return float(n)


# ---------------------------------------------------------------------------
# The articulable basket: closed-form blind adaptive policies a hand spec (Opus, from outside)
# could write. If the best of these matches the oracle, the optimal policy IS articulable ->
# below threshold. Each is `pick(table, all_cols, probe, costs, H, probed, b) -> cell|None`,
# where it may probe only `probe` cells but coverage (`determined`) is over `all_cols`.
# ---------------------------------------------------------------------------
def _simulate(spec: TrailSpec, pick) -> float:
    """Run an articulable policy against every true world, averaging determined cells. Blind (it
    sees only its own belief and the cost budget), same footing as the oracle — so the gap is
    exactly the non-articulable residue."""
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
    """Probe the affordable cell with the largest expected immediate determined-gain per unit
    cost — the myopic knapsack instinct. It grabs the clearing blocks and never starts the trail
    (signpost reads pay zero coverage, so they never top the ranking)."""
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


def lookahead_value(spec: TrailSpec, depth: int) -> float:
    """The strongest *articulable* policy: a bounded-lookahead planner. At each move it plays the
    probe optimal assuming only `depth` more *moves* (a truncated belief-MDP, cost-feasible), then
    re-plans. depth=1 is myopic; raising depth until it stops gaining locates the planning horizon
    the world demands. The verdict 'above threshold' is robust iff the full oracle still beats
    depth=2 — i.e. the optimal policy needs deeper-than-bounded planning, not a weak basket."""
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


# ---------------------------------------------------------------------------
# The ramp (bet 2). The trail payoff is convex (the valley flips on only when ALL its trail
# registers are pinned -> a cliff risk); the direct-block mass is linear and counterbalances it.
# The direct-to-valley mass ratio is the difficulty dial, exactly as in threshold.py.
# ---------------------------------------------------------------------------
def ramp_curve(spec) -> List[float]:
    """curve[k] = mean fraction of COVERAGE cells determined when a random k-subset of registers is
    known. Clearing cells: Ld per known clearing (linear in k). Valley: Lv iff the (data-dependent)
    trail registers are all known -> averaged over hypotheses (convex). Signposts are instruments,
    not coverage, so they do not appear. The linear clearing mass flattens the convex valley step
    (anti-cliff); the clearing-to-valley ratio is the difficulty dial. Generic over the spec
    protocol (`clearings`, `trail_regs`, Ld/Lv/R), so a ForkedTrailSpec's variable-depth live trail
    rides the same formula.

    M_cov is the coverage denominator (clearings + valley), not the full cell count."""
    hyps = list(product(range(spec.K), repeat=spec.R))
    n_lure, R = len(spec.clearings()), spec.R
    M_cov = spec.Ld * n_lure + spec.Lv
    out = []
    for k in range(R + 1):
        linear = k * spec.Ld * n_lure / R                      # E[clearing cells from a random k-subset]
        valley = sum(
            spec.Lv * (comb(R - d, k - d) / comb(R, k) if k >= d else 0.0)
            for d in (len(spec.trail_regs(h)) for h in hyps)
        ) / len(hyps)
        out.append((linear + valley) / M_cov if M_cov else 0.0)
    return out


def screen(spec: TrailSpec, clair: bool = True) -> dict:
    """Full model-free verdict: the threshold gap (oracle vs best articulable heuristic incl. the
    2-step planner, normalized into the floor->oracle band) plus the ramp shape. Same gate as
    `threshold.screen`, lifted to the cost-weighted B2 substrate. `clair=False` skips the
    omniscient ceiling (a per-world DP, the costly part) when sweeping many specs."""
    floor = floor_value(spec)
    oracle = oracle_value(spec)
    clairvoyant = clairvoyant_value(spec) if clair else float("nan")
    heurs = {name: _simulate(spec, pick) for name, pick in BASKET.items()}
    heurs["lookahead2"] = lookahead_value(spec, depth=2)
    best_heur = max(heurs.values())
    band = oracle - floor
    gap_norm = (oracle - best_heur) / band if band > 1e-9 else 0.0
    heur_norm = (best_heur - floor) / band if band > 1e-9 else 0.0
    curve = ramp_curve(spec)
    steps = [b - a for a, b in zip(curve, curve[1:])]
    return {
        "name": spec.name, "R": spec.R, "K": spec.K, "M": spec.M,
        "n_hyps": spec.K ** spec.R, "budget": spec.budget, "Lv": spec.Lv,
        "floor": floor, "best_heur": best_heur, "oracle": oracle, "clairvoyant": clairvoyant,
        "heurs": heurs, "gap_raw": oracle - best_heur, "gap_norm": gap_norm,
        "heur_norm": heur_norm, "ramp_r2": linearity_r2(curve),
        "ramp_maxstep": max(steps) if steps else 0.0,
        "ramp_monotone": all(s > -1e-9 for s in steps),
    }
