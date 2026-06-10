"""The Pass-3 **hidden-map family** (PLAN.md -> "The design lock" / "Pass 3") — the world where
the *topology* is hidden, not just values on a public graph.

Every earlier world (the anchor, the forked trails) published its pointer tables and hid only the
register values, so a player could pre-list every candidate chain off the public structure and the
grown rule became "list the chains, commit". Here the map itself is discovered by probing: the
world is a set of node GROUPS, and each group has ONE hidden realized path from its entry through
a public candidate lattice — which candidate each node links to, and where the path stops, are
hidden variables. Probes reveal pieces of the *shape*; betting becomes informed but never certain
— you commit budget to a region whose mapping cost you only hold a posterior over.

The enumerability constraint (PLAN.md open question 1, answered): the *family* is public and small
— a hypothesis is a tuple of independent hidden variables with per-variable ranges (each group's
path index and key, plus one shared backbone), so the scorer enumerates the full product (capped,
`validate`) and best-play stays the exact belief-MDP by simulation. The *instance* is the hidden
draw. Topology variables are just variables; `anchor.py`'s tableau/oracle machinery rides the spec
protocol (`hypotheses`, `value`, `PROBE_KINDS`/`COV_KINDS`) unchanged.

The cell layout (all public; values per hypothesis):

  * **link** cells (probeable, zero coverage) — one per node that can have a successor. Value
    encodes the node's place on its group's realized path: 0 = off the realized path, 1 = the
    path stops here, 2+j = links to candidate j of the next layer. The shape is learned ONLY
    here, one hop at a time — you must follow the realized path; probing the wrong candidate
    reads "off" and the budget is gone.
  * **key** cells (probeable, zero coverage) — one per group, reading the group's hidden key.
  * **backbone** cell (probeable, zero coverage) — the one shared variable. Pays nothing alone;
    every COUPLED group's region needs it (the multi-horizon stepping stone: one cheap probe
    that unlocks the last mile of every deep region — PLAN.md design lock 2).
  * **region** cells (coverage, NOT probeable) — a group's payoff block, inference-only:
    value = (key + backbone + path_length + pos) mod 2 (backbone only for coupled groups).
    The LENGTH term is what makes the shape load-bearing: a deep region stays undetermined
    until the path is mapped to its stop, so no key/backbone shortcut pays — the payoff sits
    strictly beyond a 2-move planning horizon, while a layerless bait group (length 0, public)
    pins on its key alone.

Probeable and coverage cells are **disjoint**, so the no-inference floor is exactly 0 — the
plodder is deleted as a runtime baseline and its job (strip free coverage) is enforced here in
the build-screen (`screen`), as PLAN.md design lock 4 moves it. Scoring is the band against
best-play alone (the optimal player *under uncertainty* — `anchor.oracle_value`, never the
clairvoyant). The taste the family demands: scout cheap structure first, weigh a region's value
against the *posterior* over its remaining mapping cost, commit, and abandon a thread the moment
the arithmetic turns — under a budget that never affords everything.

Faithful to the live student (the 2026-06-09 finding): the pointer chase is probe-mediated — the
world answers every hop, so mis-resolution cannot happen silently in-head; reconstruction at
submit is one line of arithmetic per cell; and coverage is several mid-size regions, not one
all-or-nothing valley.

Multi-goal (PLAN.md design lock 3) is present but off: `goals()` exposes the goal grouping
(today: one goal spanning every region); it surfaces to the player only when a spec carries more
than one (Pass 6).
"""

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from typing import Callable, List, Optional, Tuple

from . import anchor


# ---------------------------------------------------------------------------
# The grammar.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GroupSpec:
    """One node group: an entry plus `layers` of candidate successors (public lattice). The hidden
    realized path picks one candidate per layer and may stop at any layer >= 1 (variable length —
    the hidden depth). `layers == ()` is the degenerate bait group: length 0 is public, so one key
    probe resolves its region. `coupled` puts the shared backbone into the region law (the deep,
    multi-horizon payoff); uncoupled regions pay from the key alone (the immediate payoff)."""
    layers: Tuple[int, ...] = ()
    key_arity: int = 2
    region_len: int = 4
    coupled: bool = True

    def paths(self) -> List[Tuple[int, ...]]:
        """Every realizable path: a choice of candidate per layer, stopping at length 1..n
        (or the empty path when there are no layers). Public as a family; which one is real is
        the hidden variable."""
        if not self.layers:
            return [()]
        out: List[Tuple[int, ...]] = []
        for length in range(1, len(self.layers) + 1):
            out.extend(product(*(range(s) for s in self.layers[:length])))
        return out


@dataclass(frozen=True)
class HiddenMapSpec:
    """A hidden-map world: groups of nodes (each with a hidden realized path + a hidden key),
    one shared backbone variable (present iff any group is coupled), and the scarce cost budget.
    Hidden variables, in order: (path_g, key_g) per group, then the backbone. Everything else —
    the lattice, the cell layout, the costs, the value law — is public."""
    name: str
    groups: Tuple[GroupSpec, ...]
    budget: int
    backbone_arity: int = 2
    cost_link: int = 1
    cost_key: int = 1
    cost_backbone: int = 1

    PROBE_KINDS = ("link", "key", "backbone")
    COV_KINDS = ("region",)

    # ---- the hypothesis space (the public, enumerable family) ----
    @property
    def has_backbone(self) -> bool:
        return any(g.coupled for g in self.groups)

    def variable_ranges(self) -> Tuple[int, ...]:
        r: List[int] = []
        for g in self.groups:
            r.extend((len(g.paths()), g.key_arity))
        if self.has_backbone:
            r.append(self.backbone_arity)
        return tuple(r)

    def hypotheses(self):
        return product(*(range(n) for n in self.variable_ranges()))

    def n_hyps(self) -> int:
        n = 1
        for r in self.variable_ranges():
            n *= r
        return n

    def _path(self, hyp: Tuple[int, ...], gi: int) -> Tuple[int, ...]:
        return self.groups[gi].paths()[hyp[2 * gi]]

    def _key(self, hyp: Tuple[int, ...], gi: int) -> int:
        return hyp[2 * gi + 1]

    def _backbone(self, hyp: Tuple[int, ...]) -> int:
        return hyp[-1] if self.has_backbone else 0

    # ---- the cell layout (public addresses; values per hypothesis) ----
    def cells(self) -> List[Tuple]:
        """Probe cells first (per group: link cells for every node that can have a successor —
        the entry and layers 1..n-1 — then the group's key cell; then the backbone), regions
        last."""
        cells: List[Tuple] = []
        for gi, g in enumerate(self.groups):
            n = len(g.layers)
            if n >= 1:
                cells.append(("link", gi, 0, 0))
            for li in range(1, n):
                for idx in range(g.layers[li - 1]):
                    cells.append(("link", gi, li, idx))
            cells.append(("key", gi))
        if self.has_backbone:
            cells.append(("backbone",))
        for gi, g in enumerate(self.groups):
            for pos in range(g.region_len):
                cells.append(("region", gi, pos))
        return cells

    def cost_of(self, cell: Tuple) -> int:
        kind = cell[0]
        if kind == "link":
            return self.cost_link
        if kind == "key":
            return self.cost_key
        if kind == "backbone":
            return self.cost_backbone
        return 1  # regions are never probeable; cost is moot

    @property
    def M(self) -> int:
        return len(self.cells())

    @property
    def R(self) -> int:
        return len(self.variable_ranges())

    @property
    def K(self) -> int:
        """Max cell alphabet (display/report only — cells are ragged: links 2+max fanout, keys
        their arity, backbone its arity, regions 2)."""
        k = max(2, self.backbone_arity if self.has_backbone else 2)
        for g in self.groups:
            k = max(k, g.key_arity)
            for size in g.layers:
                k = max(k, 2 + size)
        return k

    # ---- the value law (deterministic; spec-owned via the protocol) ----
    def value(self, cell: Tuple, hyp: Tuple[int, ...]) -> int:
        kind = cell[0]
        if kind == "link":
            _, gi, li, idx = cell
            path = self._path(hyp, gi)
            if li == 0:
                return 2 + path[0]
            if len(path) < li or path[li - 1] != idx:
                return 0                       # off the realized path
            if len(path) == li:
                return 1                       # the path stops here
            return 2 + path[li]
        if kind == "key":
            return self._key(hyp, cell[1])
        if kind == "region":
            _, gi, pos = cell
            b = self._backbone(hyp) if self.groups[gi].coupled else 0
            return (self._key(hyp, gi) + b + len(self._path(hyp, gi)) + pos) % 2
        return self._backbone(hyp)             # backbone

    # ---- the public face (delegated to by episode_state.world_map; zero world-story) ----
    def world_map_public(self, remaining: int) -> dict:
        value_rule = (
            "Cell values are a deterministic lookup, never a pattern to guess. The map is a set "
            "of node GROUPS; each group hides ONE realized path: its entry links to one candidate "
            "of the next layer, and so on, stopping at a hidden depth. A link cell reads the "
            "node's place on its group's path: 0 = off the realized path, 1 = the path stops at "
            "this node, 2+j = it links to candidate j of the next layer. A key cell reads the "
            "group's hidden key; the backbone cell reads the shared backbone value. Region cells "
            "are NOT probeable — you reconstruct them: value = (key + backbone + path_length + "
            "pos) mod 2, where backbone enters only for a coupled group (see `groups`) and "
            "path_length is the realized path's length (0 for a group with no layers). So a "
            "group's whole region is forced exactly when your probes pin its key, the backbone "
            "(if coupled), and its path's length — probing links/keys/backbone pays zero "
            "coverage by itself. Submit the forced value for every region cell you can "
            "determine.")
        cells = self.cells()
        cell_entries = []
        for col, c in enumerate(cells):
            e = {"col": col, "kind": c[0], "cost": self.cost_of(c),
                 "probeable": c[0] in self.PROBE_KINDS, "coverage": c[0] in self.COV_KINDS}
            if c[0] == "link":
                e["group"], e["node"] = c[1], [c[2], c[3]]
            elif c[0] == "key":
                e["group"] = c[1]
            elif c[0] == "region":
                e["group"], e["pos"] = c[1], c[2]
            cell_entries.append(e)
        groups = [{"group": gi, "layers": list(g.layers), "coupled": g.coupled,
                   "key_arity": g.key_arity,
                   "region_cols": [col for col, c in enumerate(cells)
                                   if c[0] == "region" and c[1] == gi]}
                  for gi, g in enumerate(self.groups)]
        out = {"n_groups": len(self.groups), "budget": self.budget, "remaining": remaining,
               "value_rule": value_rule, "groups": groups,
               "backbone_col": next((col for col, c in enumerate(cells)
                                     if c[0] == "backbone"), None),
               "cells": cell_entries}
        if len(self.goals()) > 1:              # multi-goal: present but off until Pass 6
            out["goals"] = self.goals()
        return out

    def goals(self) -> List[dict]:
        """The goal grouping (PLAN.md design lock 3 — first-class interface, lit up in Pass 6).
        Today: one goal spanning every region, so nothing surfaces to the player yet."""
        cells = self.cells()
        return [{"goal": 0,
                 "region_cols": [col for col, c in enumerate(cells) if c[0] == "region"]}]

    def report_blurb(self) -> str:
        """One-line PUBLIC description for the sanitized meta/inventor report (no hidden values)."""
        shapes = "; ".join(
            f"group {gi} (layers {list(g.layers)}, region {g.region_len}, "
            f"{'coupled' if g.coupled else 'uncoupled'})" for gi, g in enumerate(self.groups))
        return (f"a hidden map of {len(self.groups)} node groups [{shapes}]: each group's realized "
                f"path (which candidate each node links to, where it stops) and its key are "
                f"hidden; regions are inference-only, keyed to the group's key and its path's "
                f"length" + (" plus a shared backbone for coupled groups" if self.has_backbone
                             else "") + "; probing links/keys/backbone pays ZERO coverage by itself")

    def describe_cell(self, cell: Tuple) -> str:
        kind = cell[0]
        if kind == "link":
            return f"link g{cell[1]}[{cell[2]},{cell[3]}]"
        if kind == "key":
            return f"key g{cell[1]}"
        if kind == "region":
            return f"region g{cell[1]}+{cell[2]}"
        return "backbone"

    # ---- declarative (de)serialization (kind-tagged; structure as data, never code) ----
    def to_dict(self) -> dict:
        return {"kind": "hidden", "name": self.name, "budget": self.budget,
                "backbone_arity": self.backbone_arity, "cost_link": self.cost_link,
                "cost_key": self.cost_key, "cost_backbone": self.cost_backbone,
                "groups": [{"layers": list(g.layers), "key_arity": g.key_arity,
                            "region_len": g.region_len, "coupled": g.coupled}
                           for g in self.groups]}

    @classmethod
    def from_dict(cls, d: dict) -> "HiddenMapSpec":
        groups = tuple(GroupSpec(layers=tuple(int(x) for x in g.get("layers", ())),
                                 key_arity=int(g.get("key_arity", 2)),
                                 region_len=int(g.get("region_len", 4)),
                                 coupled=bool(g.get("coupled", True)))
                       for g in d["groups"])
        return cls(name=d["name"], groups=groups, budget=int(d["budget"]),
                   backbone_arity=int(d.get("backbone_arity", 2)),
                   cost_link=int(d.get("cost_link", 1)), cost_key=int(d.get("cost_key", 1)),
                   cost_backbone=int(d.get("cost_backbone", 1)))


HYP_CAP = 4096  # the enumerability wall: the family must stay exactly scoreable


def validate(spec: HiddenMapSpec) -> List[str]:
    """Structural well-formedness BEFORE any oracle is derived (the integrity wall as code: a
    proposal is realized only if it is a legal, enumerable structure — never because it claims a
    score). Returns a list of problems (empty == ok)."""
    issues: List[str] = []
    if not spec.groups:
        issues.append("need at least one group")
    for gi, g in enumerate(spec.groups):
        if any(s < 1 for s in g.layers):
            issues.append(f"group {gi}: every layer needs >= 1 candidate")
        if g.key_arity < 2:
            issues.append(f"group {gi}: key_arity must be >= 2")
        if g.region_len < 1:
            issues.append(f"group {gi}: region_len must be >= 1")
    if spec.has_backbone and spec.backbone_arity < 2:
        issues.append("backbone_arity must be >= 2 when any group is coupled")
    if spec.budget < 1:
        issues.append("budget must be >= 1")
    if min(spec.cost_link, spec.cost_key, spec.cost_backbone) < 1:
        issues.append("probe costs must be >= 1")
    if not issues and spec.n_hyps() > HYP_CAP:
        issues.append(f"family too large to score exactly ({spec.n_hyps()} > {HYP_CAP} hypotheses)")
    return issues


# ---------------------------------------------------------------------------
# The reference method — the solvability witness (the analogue of world_smith's scout-then-commit):
# an articulable, blind adaptive policy proving a reachable method attains the best-play band.
# Probe the backbone (when coupled payoff exists), then develop groups richest-first, each only
# while its worst-case completion still fits the budget — key, then pin the path's depth by
# probing link cells DEEPEST LAYER FIRST (an off-path read eliminates every deeper shape at once,
# so the bottom-up order pins the length in at most one layer's worth of probes; tracing from the
# entry spends a probe per hop and learns the choices, which the region law never pays for). It
# is allowed to be articulable: *solvable* is the gate it serves; *hard* is best-play vs the
# GENERIC basket.
# ---------------------------------------------------------------------------
def _col_index(spec: HiddenMapSpec):
    """Column lookups: link col per (g, layer, idx), key col per group, the backbone col."""
    link, key, backbone = {}, {}, None
    for col, c in enumerate(spec.cells()):
        if c[0] == "link":
            link[(c[1], c[2], c[3])] = col
        elif c[0] == "key":
            key[c[1]] = col
        elif c[0] == "backbone":
            backbone = col
    return link, key, backbone


def _pinned(table, H, col) -> Optional[int]:
    if col is None:
        return None
    rep = next(iter(H))
    v = table[rep][col]
    return v if all(table[h][col] == v for h in H) else None


def reference_method(spec: HiddenMapSpec) -> Callable:
    """The pick (anchor._simulate contract). Closes over the public structure only; reads hidden
    values solely through its refined belief H (blind, same footing as the oracle)."""
    link_col, key_col, backbone_col = _col_index(spec)
    order = sorted(range(len(spec.groups)), key=lambda gi: -spec.groups[gi].region_len)
    # Path lengths per tableau row, per group — for the "is the length pinned yet" check.
    rows = list(spec.hypotheses())
    lens = [[len(spec._path(h, gi)) for h in rows] for gi in range(len(spec.groups))]

    def length_pinned(H, gi) -> bool:
        it = iter(H)
        first = lens[gi][next(it)]
        return all(lens[gi][h] == first for h in it)

    def next_link(table, H, gi):
        """The next depth-pinning probe: the first still-informative link cell of the group,
        deepest layer first. Returns (col or None, worst-case informative links left in that
        deepest layer — the upper bound on what pinning the length can still cost)."""
        layer_cols: dict = {}
        for (g, li, idx), col in link_col.items():
            if g == gi:
                layer_cols.setdefault(li, []).append(col)
        for li in sorted(layer_cols, reverse=True):
            live = [c for c in layer_cols[li]
                    if _pinned(table, H, c) is None and len(anchor._partition(table, H, c)) > 1]
            if live:
                return live[0], len(live)
        return None, 0

    def pick(table, cov, probe, costs, H, probed, b):
        if backbone_col is not None and _pinned(table, H, backbone_col) is None \
                and backbone_col not in probed and costs[backbone_col] <= b:
            return backbone_col
        for gi in order:
            need = 0 if _pinned(table, H, key_col[gi]) is not None else spec.cost_key
            if not length_pinned(H, gi):
                col, worst = next_link(table, H, gi)
                need += worst * spec.cost_link
            else:
                col = None
            if need == 0 or need > b:
                continue                        # resolved, or not worth starting/finishing
            if _pinned(table, H, key_col[gi]) is None and key_col[gi] not in probed:
                return key_col[gi]
            if col is not None and col not in probed:
                return col
        return None
    return pick


# ---------------------------------------------------------------------------
# The build-screen (PLAN.md Pass 3a). Model-free, deterministic, token-free. Gates:
#   * no-free-coverage — the no-inference floor must be ~0 (the plodder's old job, moved here);
#   * hard / solver-proof — best-play (the belief-MDP oracle, by simulation) beats every generic
#     planner (greedy-info, greedy-determined, 2-step lookahead) by >= MARGIN of the band;
#   * solvable — the articulable reference method reaches the band ceiling (>= SOLVE_BAR);
#   * anti-cliff — no single region is most of the coverage mass (the all-or-nothing lesson);
#   * room — the best generic planner lands mid-band (a live student has reachable room).
# ---------------------------------------------------------------------------
MARGIN = 0.15
SOLVE_BAR = 0.85
CLIFF = 0.55
HEUR_LO, HEUR_HI = 0.10, 0.80


@lru_cache(maxsize=None)
def screen(spec: HiddenMapSpec) -> dict:
    issues = validate(spec)
    if issues:
        return {"name": spec.name, "valid": False, "issues": issues, "ship": False}
    floor = anchor.floor_value(spec)
    oracle = anchor.oracle_value(spec)
    heurs = {name: anchor._simulate(spec, pick) for name, pick in anchor.BASKET.items()}
    heurs["lookahead2"] = anchor.lookahead_value(spec, depth=2)
    best_heur = max(heurs.values())
    method = anchor._simulate(spec, reference_method(spec))
    band = oracle - floor
    gap_norm = (oracle - best_heur) / band if band > 1e-9 else 0.0
    heur_norm = (best_heur - floor) / band if band > 1e-9 else 0.0
    method_norm = (method - floor) / band if band > 1e-9 else 0.0
    cov_mass = sum(g.region_len for g in spec.groups)
    cliff = max(g.region_len for g in spec.groups) / cov_mass if cov_mass else 1.0
    gates = {
        "no_free_coverage": floor <= 1e-9,
        "hard": gap_norm >= MARGIN,
        "solvable": method_norm >= SOLVE_BAR and oracle > floor + 1e-9,
        "anti_cliff": cliff <= CLIFF,
        "room": HEUR_LO <= heur_norm <= HEUR_HI,
    }
    return {"name": spec.name, "valid": True, "issues": [],
            "n_hyps": spec.n_hyps(), "n_probe_cols": len(anchor.build_tableau(spec)[4]),
            "budget": spec.budget, "floor": floor, "oracle": oracle,
            "heurs": heurs, "best_heur": best_heur, "method": method,
            "gap_norm": gap_norm, "heur_norm": heur_norm, "method_norm": method_norm,
            "cliff": cliff, **gates, "ship": all(gates.values())}


# ---------------------------------------------------------------------------
# The canonical world — the build-screened run-pick (see run_hiddenmap.py for the sweep that
# chose it). One deep coupled group (hidden depth 1..3 — the posterior-priced commitment), one
# mid coupled group (depth fixed at 1, reachable by a bounded planner — the middle tier), two
# layerless bait groups (the myopic gradient), one backbone.
# ---------------------------------------------------------------------------
def canonical_spec() -> HiddenMapSpec:
    return HiddenMapSpec(
        name="hidden-map",
        groups=(GroupSpec(layers=(2, 2, 2), region_len=8, coupled=True),
                GroupSpec(layers=(2,), region_len=5, coupled=True),
                GroupSpec(layers=(), region_len=2, coupled=False),
                GroupSpec(layers=(), region_len=2, coupled=False)),
        budget=6)
