"""The threshold screen — the gate that decides whether a world can earn the loop's keep.

`ROADMAP.md` -> "earning its keep" turned the project's honest null into an operational
gate: *can Opus write the optimal allocation policy in closed form, given full information?*
If yes, a hand spec is competitive and any taste-gap is noise (exactly what the three tape
slices measured). Only a world where the answer is **no** — the policy is found by playing,
not deducible by inspection — can the loop climb past an articulable ceiling.

This module makes that gate **cheap and model-free**. The dividing line is one property:
**adaptive submodularity**. The tape-world (`grammar.py`) scores coverage by a knapsack over
*independent* per-segment value curves -> the optimal adaptive policy is greedy -> a five-line
formula -> below threshold. A world is **above** threshold when value-of-information is
**non-submodular**: probes are *complementary*, the belief state does not factor, and the
optimal probe order is itself a hard search with no closed form.

The screen, made operational (the reusable artifact):

  > A world is above threshold iff the exact **belief-MDP oracle** (the optimal *adaptive*
  > policy, computed by value iteration over belief states) materially beats the **best of a
  > basket of articulable heuristics** (greedy info-gain, greedy determined-gain).

The crucial property that keeps this both *affordable* and *above the line*: **computable
!= expressible.** On a small world the oracle is exactly computable in pure compute (a finite
belief tree, no LLM tokens — the integrity floor stays intact, we keep our references); but
when the world is coupled there is no *formula* that expresses the optimal policy, so Opus
cannot write it. Toy in tokens and world-size, not toy in policy-structure.

The substrate here is a **register world** — a strict generalization of the tape:

  * `R` hidden registers, each an integer in `0..K-1` (the genuinely hidden seed).
  * **direct blocks**: a length-`Ld` run keyed on one register `i`; cell `p` = `(r_i + p) % K`.
    One probe pins `r_i`, which determines the whole block. Independent, submodular, *linear
    partial credit* (the ramp, bet 2).
  * **linked blocks**: a length-`Ll` run keyed on a register pair `(i, j)` with *position-
    varying* coefficients; cell `p` = `((p+1)*r_i + r_j + p) % K`. A probe reveals an
    **equation, not a value** — the block is pinned only by *combining* observations (two local
    probes, or both registers known from elsewhere). That non-self-determination is the
    complementarity. (A *sum* coupling `(r_i+r_j)` was the first attempt and it failed
    informatively: one probe pins the sum and thus the whole block, so it stays submodular and
    reads gap 0 everywhere. The coupling must be non-self-determining to bite.)

Naming a subset of registers `direct` makes the rest **hidden** — they have no direct block and
are readable only through a linked block once a neighbor is pinned: the design's "high-value
region behind a boring door". `edges = ()` with all-direct recovers the independent tape (below
threshold, the control). The gap lives in *asymmetric* coupling — a buried cluster of hidden
registers behind a lure anchor — where covering it under a scarce budget is a budgeted
densest-subgraph choice (NP-hard, non-submodular). Symmetric coupling stays greedy-solvable. The
direct-to-linked mass ratio is the difficulty dial: more links lift the gap but bend the ramp
toward a cliff; more direct mass flattens the ramp but dilutes the gap; the band is where both
hold (and the sweep shows it is narrow).

Everything is a dumb deterministic `f(structure, observations)` over an enumerated hypothesis
set — the same integrity floor as `grammar.py`, only the value-of-information is now coupled.
"""

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations, product
from typing import Dict, List, Tuple

from .grammar import linearity_r2  # reuse the ramp R^2 (bet 2)

# A cell is an AFFINE form over the registers: value = (coeffs . r + const) % K. This is the
# key to genuine coupling. A *sum* form (coeffs all 1) is self-determining — one probe pins the
# block — so it stays submodular (the first design's mistake). A form with position-varying
# coefficients reveals an *equation*, not a value: a linked block is pinned only by COMBINING
# observations (two local probes, or its registers known from elsewhere). That non-self-
# determination is exactly the complementarity that pushes a world above the threshold.
Cell = Tuple[Tuple[int, ...], int]  # (coeffs over the R registers, const)


@dataclass(frozen=True)
class LinkSpec:
    """A register world. Compact by construction; `edges` (and which registers are `direct`) is
    the coupling dial. The hidden information is the register assignment (K**R hypotheses); the
    block structure is known to everyone, exactly as the tape's family is known but its seed is
    not. `direct=None` means every register gets a direct block; naming a subset makes the rest
    **hidden** — readable only through a linked block once a neighbor is pinned (the design's
    'high-value region behind a boring door', made structural)."""
    name: str
    R: int                              # number of hidden registers
    K: int                              # colors per register
    Ld: int                             # direct-block length (per direct register)
    Ll: int                             # linked-block length (per edge)
    edges: Tuple[Tuple[int, int], ...]  # register pairs that get an affine linked block
    budget: int                         # scarce probe allowance
    direct: Tuple[int, ...] = None      # registers with a direct block (default: all)

    def direct_regs(self) -> Tuple[int, ...]:
        return tuple(range(self.R)) if self.direct is None else self.direct

    def cells(self) -> List[Cell]:
        """The fixed cell layout both agents see (they infer only the register values).
        Direct cell: coeff e_i, const p -> value (r_i + p), one probe pins r_i. Linked cell on
        (i,j) at position p: coeff (p+1) on r_i and 1 on r_j -> an equation in two unknowns, so
        the block needs both registers (or two independent local probes) to determine."""
        out: List[Cell] = []
        for i in self.direct_regs():
            for p in range(self.Ld):
                coeffs = [0] * self.R
                coeffs[i] = 1
                out.append((tuple(coeffs), p))
        for (i, j) in self.edges:
            for p in range(self.Ll):
                coeffs = [0] * self.R
                coeffs[i] = (p + 1) % self.K
                coeffs[j] = 1
                out.append((tuple(coeffs), p))
        return out

    @property
    def M(self) -> int:
        return len(self.cells())


def cell_regs(coeffs: Tuple[int, ...]) -> Tuple[int, ...]:
    """The registers a cell actually depends on (nonzero coefficient) — for the ramp curve."""
    return tuple(r for r, a in enumerate(coeffs) if a != 0)


def cell_value(coeffs: Tuple[int, ...], const: int, hyp: Tuple[int, ...], K: int) -> int:
    """Deterministic expander, one cell: an affine form over the registers, mod K."""
    return (sum(a * hyp[r] for r, a in enumerate(coeffs)) + const) % K


# ---------------------------------------------------------------------------
# The hypothesis tableau: every world the register seed can produce, as a value per cell.
# This is the version space; probing partitions it. Small by construction (K**R rows).
# ---------------------------------------------------------------------------
def build_tableau(spec: LinkSpec) -> Tuple[Tuple[Tuple[int, ...], ...], List[Cell]]:
    """Rows = hypotheses (register assignments); columns = cells. row[h][c] is the value of
    cell c under hypothesis h. The true world is one row; the agent never knows which."""
    cells = spec.cells()
    hyps = list(product(range(spec.K), repeat=spec.R))
    table = tuple(
        tuple(cell_value(coeffs, const, h, spec.K) for (coeffs, const) in cells)
        for h in hyps
    )
    return table, cells


def determined(table, cols: Tuple[int, ...], H: frozenset) -> int:
    """How many cells are LOGICALLY pinned given the consistent hypothesis set H — i.e. every
    surviving hypothesis agrees on them. The dumb deterministic coverage measure; no LLM. This
    is where coupling bites: a linked cell is pinned only once H has collapsed enough that the
    register *combination* is fixed, which can require probes in several blocks at once."""
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


# ---------------------------------------------------------------------------
# The belief-MDP oracle: the optimal ADAPTIVE policy, by exact value iteration over belief
# states. Computable in pure compute on a small world (no LLM tokens) but NOT expressible in
# closed form when the world is coupled — which is precisely the threshold being cleared.
# ---------------------------------------------------------------------------
def oracle_value(spec: LinkSpec, budget: int = None) -> float:
    """Expected cells determined by the optimal blind adaptive policy under the probe budget.
    The policy never sees the true world; it maximizes the *expected* determined-count over its
    posterior (uniform over the consistent set, since observations are deterministic and the
    register prior is uniform). This is THE optimal allocation policy the threshold asks about —
    the ceiling a hand-written policy is measured against."""
    B = spec.budget if budget is None else budget
    table, cells = build_tableau(spec)
    cols = tuple(range(len(cells)))
    H0 = frozenset(range(len(table)))

    @lru_cache(maxsize=None)
    def V(H: frozenset, b: int) -> float:
        base = determined(table, cols, H)  # the "stop" value; probing can only weakly improve
        if b == 0:
            return float(base)
        best = float(base)
        for c in cols:
            groups = _partition(table, H, c)
            if len(groups) == 1:
                continue  # non-informative probe (every world agrees) — never optimal to waste
            exp = sum(len(g) / len(H) * V(g, b - 1) for g in groups.values())
            if exp > best:
                best = exp
        return best

    return V(H0, B)


def clairvoyant_value(spec: LinkSpec, budget: int = None) -> float:
    """A higher, *omniscient* ceiling: per true world, the best fixed B-probe set chosen with
    knowledge of that world (the analog of `grammar.oracle_determined`), averaged over worlds.
    belief-MDP <= clairvoyant always; the gap is the price of uncertainty. Reported for context
    — it is NOT the threshold reference (it knows the answer, so it is trivially articulable)."""
    B = spec.budget if budget is None else budget
    table, cells = build_tableau(spec)
    cols = list(range(len(cells)))
    total = 0.0
    for h in range(len(table)):
        best = 0
        for subset in combinations(cols, min(B, len(cols))):
            H = frozenset(
                g for g in range(len(table))
                if all(table[g][c] == table[h][c] for c in subset)
            )
            best = max(best, determined(table, tuple(cols), H))
        total += best
    return total / len(table)


def floor_value(spec: LinkSpec, budget: int = None) -> float:
    """No-inference walker: it knows only the cells it directly probed (it never reads the
    structure to predict the unseen). The dumb baseline that proves *inference*, not probing,
    is doing the work. Mirrors `grammar.floor_determined`."""
    B = spec.budget if budget is None else budget
    return float(min(B, spec.M))


# ---------------------------------------------------------------------------
# The articulable basket: the closed-form policies a hand spec (Opus, from outside) could
# write. Each is a blind adaptive policy `pick(table, cols, H, probed) -> cell`. If the best of
# these matches the belief-MDP oracle, the optimal policy IS articulable -> below threshold.
# ---------------------------------------------------------------------------
def _simulate(spec: LinkSpec, pick) -> float:
    """Run an articulable policy against every true world, averaging determined cells. The
    policy is blind (it sees only its own belief, never the true world) — same footing as the
    oracle, so the gap between them is exactly the non-articulable (tacit) residue."""
    B = spec.budget
    table, cells = build_tableau(spec)
    cols = tuple(range(len(cells)))
    total = 0.0
    for h_star in range(len(table)):
        H = frozenset(range(len(table)))
        probed: set = set()
        for _ in range(B):
            c = pick(table, cols, H, probed)
            if c is None:
                break
            probed.add(c)
            v = table[h_star][c]
            H = frozenset(g for g in H if table[g][c] == v)
        total += determined(table, cols, H)
    return total / len(table)


def _greedy_info(table, cols, H, probed):
    """Probe the cell that most shrinks the belief in expectation (max information gain). The
    canonical articulable policy. Minimizing sum |group|^2 maximizes expected refinement."""
    best_c, best_score = None, None
    for c in cols:
        if c in probed:
            continue
        groups = _partition(table, H, c)
        if len(groups) == 1:
            continue
        score = -sum(len(g) ** 2 for g in groups.values())  # higher = more informative
        if best_score is None or score > best_score:
            best_c, best_score = c, score
    return best_c


def _greedy_determined(table, cols, H, probed):
    """Probe the cell with the largest expected immediate gain in determined cells — the
    tape-world's near-optimal myopic policy (the knapsack instinct). On a submodular world this
    matches the oracle; on a coupled world it underinvests in complementary probes."""
    base = determined(table, cols, H)
    best_c, best_gain = None, None
    for c in cols:
        if c in probed:
            continue
        groups = _partition(table, H, c)
        if len(groups) == 1:
            continue
        exp = sum(len(g) / len(H) * determined(table, cols, g) for g in groups.values())
        gain = exp - base
        if best_gain is None or gain > best_gain:
            best_c, best_gain = c, gain
    return best_c


BASKET = {"greedy_info": _greedy_info, "greedy_determined": _greedy_determined}


def lookahead_value(spec: LinkSpec, depth: int) -> float:
    """A bounded-lookahead planner — the *strongest articulable* policy in the basket. At each
    step it plays the probe that is optimal assuming only `depth` more probes (a truncated
    belief-MDP), then re-plans. depth=1 is myopic greedy; depth=budget is the full oracle. The
    point: if the full oracle still beats depth=2, the optimal policy needs planning deeper than
    any shallow rule — it is genuinely not closed-form, not merely beyond a myopic heuristic.
    This is what makes the 'above threshold' verdict robust to 'your basket was just weak'."""
    B = spec.budget
    table, cells = build_tableau(spec)
    cols = tuple(range(len(cells)))

    @lru_cache(maxsize=None)
    def V(H: frozenset, t: int) -> float:
        base = determined(table, cols, H)
        if t == 0:
            return float(base)
        best = float(base)
        for c in cols:
            groups = _partition(table, H, c)
            if len(groups) == 1:
                continue
            exp = sum(len(g) / len(H) * V(g, t - 1) for g in groups.values())
            if exp > best:
                best = exp
        return best

    total = 0.0
    for h_star in range(len(table)):
        H = frozenset(range(len(table)))
        probed: set = set()
        for _ in range(B):
            d = min(depth, B - len(probed))
            best_c, best = None, None
            for c in cols:
                if c in probed:
                    continue
                groups = _partition(table, H, c)
                if len(groups) == 1:
                    continue
                exp = sum(len(g) / len(H) * V(g, d - 1) for g in groups.values())
                if best is None or exp > best:
                    best_c, best = c, exp
            if best_c is None:
                break
            probed.add(best_c)
            v = table[h_star][best_c]
            H = frozenset(g for g in H if table[g][best_c] == v)
        total += determined(table, cols, H)
    return total / len(table)


# ---------------------------------------------------------------------------
# The ramp (bet 2), for the coupled world. Coupling bends it: linked cells need *both*
# endpoints, so coverage is convex (supermodular) in the registers pinned -> a cliff risk the
# direct-block mass counterbalances. The link-to-direct ratio trades gap against curvature.
# ---------------------------------------------------------------------------
def ramp_curve(spec: LinkSpec) -> List[float]:
    """curve[k] = mean fraction of cells determined when a random k-subset of registers is
    fully known (direct blocks of those registers + linked blocks with both endpoints known).
    Linear => ramp; convex hockey-stick => cliff. Structural, model-free, free."""
    cells = spec.cells()
    M = spec.M
    out = []
    for k in range(spec.R + 1):
        subs = list(combinations(range(spec.R), k))
        mean = sum(
            sum(1 for (coeffs, _) in cells if set(cell_regs(coeffs)) <= set(sub))
            for sub in subs
        ) / len(subs)
        out.append(mean / M if M else 0.0)
    return out


def screen(spec: LinkSpec) -> dict:
    """The full model-free verdict on a world: the threshold gap (oracle vs best articulable
    heuristic, normalized into the floor->oracle band), plus the ramp shape.

    Two ramp numbers, because a *coupled* world cannot have R^2 = 1.0 — that is the signature
    of an *independent*, below-threshold world (edges that need both endpoints make coverage
    supermodular, hence convex, by definition). So the bet-2 check for a coupled world is
    **anti-cliff**, not linearity: `ramp_maxstep` (the largest single jump in the ramp curve)
    must stay well below 1.0, i.e. no all-or-nothing step where partial inference buys nothing
    then everything. `ramp_r2` is kept only as reported context."""
    floor = floor_value(spec)
    oracle = oracle_value(spec)
    clair = clairvoyant_value(spec)
    heurs = {name: _simulate(spec, pick) for name, pick in BASKET.items()}
    heurs["lookahead2"] = lookahead_value(spec, depth=2)  # strongest articulable: 2-step planner
    best_heur = max(heurs.values())
    band = oracle - floor
    gap_norm = (oracle - best_heur) / band if band > 1e-9 else 0.0
    heur_norm = (best_heur - floor) / band if band > 1e-9 else 0.0
    curve = ramp_curve(spec)
    steps = [b - a for a, b in zip(curve, curve[1:])]
    return {
        "name": spec.name, "R": spec.R, "K": spec.K, "M": spec.M,
        "n_hyps": spec.K ** spec.R, "budget": spec.budget, "edges": len(spec.edges),
        "floor": floor, "best_heur": best_heur, "oracle": oracle, "clairvoyant": clair,
        "heurs": heurs, "gap_raw": oracle - best_heur, "gap_norm": gap_norm,
        "heur_norm": heur_norm, "ramp_r2": linearity_r2(curve),
        "ramp_maxstep": max(steps) if steps else 0.0,
        "ramp_monotone": all(s > -1e-9 for s in steps),
    }
