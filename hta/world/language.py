"""The **world language** — the part-box the world-smith composes worlds out of (DESIGN.md §5).

What we hand the smith is neither a finished world nor bare principles: it is a *grammar*. A
small box of part types plus the rules for wiring them. The smith writes a parts-list; the lab
checks it is well-formed (`validate`), builds the world (`build_tableau`), and re-derives the
answer key mechanically (`hta/world/grade.py`) — all because the parts are ours. The smith's
freedom is everything the parts combine into; the safety is everything the language *cannot* say
(it cannot describe a world we cannot grade). Each world it writes is one instance, disposable.

The first slice (the kit's first cut, §9.2). Three part types over a shared pool of R hidden
variables (K colors each — the seed):

  * **clearing** — a variable carrying a fat *direct* coverage block (length `Ld`). One probe pins
    it; it pays immediately. The off-trail bait, and the thing a lazy allocator grabs.
  * **chain** — a sequence of public pointer hops from a `head` variable to a *landmark* variable.
    Each register on it is read as a cheap **signpost** that pays ZERO coverage (an instrument, not
    a map cell). The hidden values fix where the chain ends, so its content is learnable only by
    playing this instance.
  * **fork** — a region that bundles a **gate ladder** (one or more signpost variables whose hidden
    values select which of its chains is *live*) with its candidate chains and a deep **valley**
    (length `Lv`) that mirrors the LIVE chain's landmark. The valley is inference-only: you
    reconstruct it by reading the gate(s) then walking the live chain — never by drilling it, and no
    prefix of the walk pays. A fork with one chain and no ladder is a plain trail (the anchor); a
    fork with several chains and a gate is the decoy; with a gate *ladder*, the adaptive ladder.

A `WorldSpec` is a list of such regions over the variable pool plus the scarce cost budget. This
subsumes the whole trail family (`hta/_trail`) as single-fork instances, and goes past it: several
forks and standalone clearings compose into one world (a *position* with more than one structured
region to read). That composition is what makes this a language, not a world.

Everything here is a dumb deterministic `f(structure, observations)`: the value law is a lookup
(`cell_value`), never a pattern to guess — that is the integrity floor's B2 line (reconstruction is
inference-free; only *allocation* is hard). The (de)serialization is data, never code (safe-eval
lifted): the smith proposes a validated parts-list, the expander realizes it.
"""

from dataclasses import dataclass, field
from itertools import product
from math import comb
from typing import List, Tuple, Union


# ---------------------------------------------------------------------------
# Parts.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Chain:
    """One candidate trail: a `head` signpost variable, then public pointer `hops`. Walking it under
    a hypothesis reads the head's hidden value to pick the next variable, and so on, ending on a
    landmark variable. Each hop is a length-K table (current-var value -> next variable), so *which*
    variable the chain ends on is the hidden seed, never readable off the public structure.
    Depth = 1 + len(hops)."""
    head: int
    hops: Tuple[Tuple[int, ...], ...] = ()

    @property
    def depth(self) -> int:
        return 1 + len(self.hops)

    def walk(self, K: int, hyp: Tuple[int, ...]) -> List[int]:
        """The variables this chain visits under `hyp` (head, then each hop's target). The last is
        the landmark. Data-dependent: that is the hidden content."""
        r, visited = self.head, [self.head]
        for hop in self.hops:
            r = hop[hyp[r] % K]
            visited.append(r)
        return visited

    def vars(self) -> set:
        regs = {self.head}
        for hop in self.hops:
            regs.update(hop)
        return regs


@dataclass(frozen=True)
class Clearing:
    """A variable carrying a fat direct coverage block of length `Ld` — a big immediate payoff for
    one probe, sitting OFF any trail. The bait a greedy allocator takes instead of walking a trail."""
    var: int
    Ld: int = 2


@dataclass(frozen=True)
class Fork:
    """A selector-gated region: a **gate ladder** picks which chain is live, the live chain's
    landmark drives a **valley** of `Lv` inference-only coverage cells.

    The gate can be a single variable (`gate_hops=()`, the decoy) or an adaptive **ladder**
    (`gate_hops`: each hop maps the current gate's value -> the next gate variable, so you must scout
    the gates step by step). The FINAL gate's value selects the live chain
    (`chains[final_gate_value % n_chains]`). One chain makes the gate degenerate (a plain trail)."""
    chains: Tuple[Chain, ...]
    gate: int
    Lv: int = 9
    gate_hops: Tuple[Tuple[int, ...], ...] = ()

    @property
    def n_chains(self) -> int:
        return len(self.chains)

    def gate_chain(self, K: int, hyp: Tuple[int, ...]) -> List[int]:
        """The gate variables the selector ladder visits under `hyp` (the first gate, then each
        gate-hop's target). The LAST is the final gate. With no `gate_hops` this is just `[gate]`."""
        r, visited = self.gate, [self.gate]
        for hop in self.gate_hops:
            r = hop[hyp[r] % K]
            visited.append(r)
        return visited

    def final_gate(self, K: int, hyp: Tuple[int, ...]) -> int:
        return self.gate_chain(K, hyp)[-1]

    def live_index(self, K: int, hyp: Tuple[int, ...]) -> int:
        return hyp[self.final_gate(K, hyp)] % self.n_chains

    def live_chain(self, K: int, hyp: Tuple[int, ...]) -> Chain:
        return self.chains[self.live_index(K, hyp)]

    def landmark_reg(self, K: int, hyp: Tuple[int, ...]) -> int:
        """The LIVE chain's landmark — the variable the valley mirrors."""
        return self.live_chain(K, hyp).walk(K, hyp)[-1]

    def trail_regs(self, K: int, hyp: Tuple[int, ...]) -> Tuple[int, ...]:
        """The variables that must ALL be pinned before this valley flips on: every variable the live
        chain visits, PLUS the whole gate ladder iff there is a real fork (n_chains > 1). Reading the
        wrong chain, or only the first rung of the ladder, pins none of the rest — the strategy trap."""
        visited = self.live_chain(K, hyp).walk(K, hyp)
        head = self.gate_chain(K, hyp) if self.n_chains > 1 else []
        return tuple(dict.fromkeys([*head, *visited]))

    def signpost_vars(self) -> set:
        regs = {self.gate}
        for hop in self.gate_hops:
            regs.update(hop)
        for ch in self.chains:
            regs |= ch.vars()
        return regs


Region = Union[Clearing, Fork]


# ---------------------------------------------------------------------------
# The world: a parts-list over a shared variable pool.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WorldSpec:
    """A world as a list of `regions` (clearings + forks) over R hidden variables, K colors each,
    under a scarce COST `budget`. Public to everyone: the regions' wiring, the cell layout, the
    costs, the budget, and the deterministic value law. Hidden (the seed): the K**R variable
    assignment — which fixes, per fork, which chain is live and where it ends. Different seeds realize
    different shapes, so the winning policy's CONTENT is learnable only by playing the instance."""
    name: str
    R: int
    K: int
    regions: Tuple[Region, ...]
    budget: int
    Ls: int = 1                     # signpost cell length (a pointer, kept tiny: not payoff)
    cost_signpost: int = 1          # cost to read a signpost / gate (the cheap door)
    cost_clearing: int = 1          # cost to probe a clearing block (the variable-cost knob)

    # ---- region views ----
    def forks(self) -> List[Fork]:
        return [r for r in self.regions if isinstance(r, Fork)]

    def clearing_regions(self) -> List[Clearing]:
        return [r for r in self.regions if isinstance(r, Clearing)]

    def signpost_vars(self) -> set:
        regs: set = set()
        for f in self.forks():
            regs |= f.signpost_vars()
        return regs

    def clearing_vars(self) -> List[int]:
        return [c.var for c in self.clearing_regions()]

    # ---- the cell layout (the column descriptors; values are per-hypothesis) ----
    def cells(self) -> List[Tuple]:
        """Cheap signpost cells (instruments), then the fat clearing blocks (immediate bait), then
        each fork's valley (the deep, trail-gated payoff). A valley cell is tagged with its fork's
        index into `regions`, so `cell_value` resolves the right live chain."""
        cells: List[Tuple] = []
        for v in sorted(self.signpost_vars()):
            for p in range(self.Ls):
                cells.append(("sig", v, p))
        for cl in self.clearing_regions():
            for p in range(cl.Ld):
                cells.append(("direct", cl.var, p))
        for idx, r in enumerate(self.regions):
            if isinstance(r, Fork):
                for p in range(r.Lv):
                    cells.append(("valley", idx, p))
        return cells

    def cost_of(self, cell: Tuple) -> int:
        return self.cost_signpost if cell[0] == "sig" else self.cost_clearing

    @property
    def M(self) -> int:
        return len(self.cells())

    # ---- the deterministic value law (a lookup, never a pattern to guess: the B2 line) ----
    def cell_value(self, cell: Tuple, hyp: Tuple[int, ...]) -> int:
        kind = cell[0]
        if kind in ("sig", "direct"):
            _, var, pos = cell
            return (hyp[var] + pos) % self.K
        _, region_idx, pos = cell                       # valley
        fork = self.regions[region_idx]
        return (hyp[fork.landmark_reg(self.K, hyp)] + pos) % self.K

    def trail_regs(self, hyp: Tuple[int, ...]) -> Tuple[int, ...]:
        """Every variable load-bearing for some valley under `hyp` (the union over forks)."""
        regs: List[int] = []
        for f in self.forks():
            regs.extend(f.trail_regs(self.K, hyp))
        return tuple(dict.fromkeys(regs))

    # ---- the ramp (the anti-cliff difficulty shape, intrinsic to the parts) ----
    def ramp_curve(self) -> List[float]:
        """curve[k] = mean fraction of COVERAGE cells determined when a random k-subset of variables
        is known. Clearing cells are linear in k (Ld per known clearing); each fork's valley is convex
        (Lv iff all its trail variables are known) — averaged over hypotheses. The linear clearing
        mass flattens the convex valley step (the anti-cliff); the clearing-to-valley ratio is the
        difficulty dial. Signposts are instruments, not coverage, so they never appear."""
        hyps = list(product(range(self.K), repeat=self.R))
        clearing_mass = sum(c.Ld for c in self.clearing_regions())
        valley_mass = sum(f.Lv for f in self.forks())
        M_cov = clearing_mass + valley_mass
        if not M_cov:
            return [0.0] * (self.R + 1)
        out = []
        for k in range(self.R + 1):
            linear = k * clearing_mass / self.R
            valley = 0.0
            for f in self.forks():
                depths = [len(f.trail_regs(self.K, h)) for h in hyps]
                valley += f.Lv * sum(
                    (comb(self.R - d, k - d) / comb(self.R, k) if k >= d else 0.0) for d in depths
                ) / len(hyps)
            out.append((linear + valley) / M_cov)
        return out

    # ---- the public face (delegated to by the episode airgap; no hidden values) ----
    def world_map_public(self, remaining: int) -> dict:
        """The PUBLIC rules of the game: the regions' wiring, the cell layout with costs/roles, and
        the deterministic value law. The variable VALUES are absent — that is the hidden seed.
        Exposing the law (not the values) makes reconstruction a reachable LOOKUP; what stays hidden,
        and the whole game, is the ALLOCATION. Generic vocabulary (variable/value, cells/regions/
        budget/coverage): no world-story leaks, so the player cannot overfit the container."""
        value_rule = (
            "Cell values are a deterministic lookup, never a pattern to guess: a cell's value = "
            "(its variable's hidden value + pos) mod K. A cell with a `var` field uses that variable. "
            "A cell marked mirrors='target' belongs to a FORK region: the fork's gate ladder selects "
            "which chain is live (final gate's value mod n_chains), and you walk that chain's pointer "
            "hops to its target variable; the cell mirrors the target. So to reconstruct a fork's "
            "valley you must pin its gate ladder (which chain is live) AND that chain's variables "
            "(its target value) — walking the wrong chain, or skipping any gate, pins nothing of it. "
            "Once a variable's value is pinned, every cell keyed to it is fully determined.")
        return {"R": self.R, "K": self.K, "budget": self.budget, "remaining": remaining,
                "value_rule": value_rule, "regions": self._public_regions(),
                "cells": public_cells(self)}

    def _public_regions(self) -> List[dict]:
        out = []
        for idx, r in enumerate(self.regions):
            if isinstance(r, Clearing):
                out.append({"region": idx, "kind": "clearing", "var": r.var, "length": r.Ld})
            else:
                out.append({"region": idx, "kind": "fork", "gate": r.gate,
                            "gate_hops": [list(h) for h in r.gate_hops], "n_chains": r.n_chains,
                            "chains": [{"head": ch.head, "hops": [list(h) for h in ch.hops]}
                                       for ch in r.chains],
                            "selects": "chains[final_gate_value % n_chains] is the LIVE chain; the "
                                       "final gate is reached by walking the gate ladder"})
        return out

    def report_blurb(self) -> str:
        """One-line PUBLIC description for the sanitized meta/inventor report (no hidden values)."""
        parts = []
        for r in self.regions:
            if isinstance(r, Clearing):
                parts.append(f"a clearing (var {r.var}) paying {r.Ld} cells immediately")
            else:
                gate = (f"gate {r.gate}" if not r.gate_hops else
                        f"an adaptive gate ladder (gate {r.gate}, hops {[list(h) for h in r.gate_hops]})")
                parts.append(f"a fork ({r.n_chains} chains, {gate}) whose live chain drives a deep "
                             f"{r.Lv}-cell valley")
        return (f"a world over {self.R} variables (values 0..{self.K - 1} hidden): " + "; ".join(parts)
                + ". Reading a signpost/gate pays ZERO coverage; clearings pay immediately; a valley "
                "pays only once its gate(s) are scouted and its live chain is walked end to end")

    # ---- declarative (de)serialization: the smith proposes/realizes STRUCTURE as data ----
    def to_dict(self) -> dict:
        return {"name": self.name, "R": self.R, "K": self.K, "budget": self.budget,
                "Ls": self.Ls, "cost_signpost": self.cost_signpost,
                "cost_clearing": self.cost_clearing, "regions": [_region_to_dict(r) for r in self.regions]}

    @classmethod
    def from_dict(cls, d: dict) -> "WorldSpec":
        regions = tuple(_region_from_dict(r) for r in d["regions"])
        return cls(name=d.get("name", "proposed"), R=int(d["R"]), K=int(d["K"]),
                   regions=regions, budget=int(d["budget"]), Ls=int(d.get("Ls", 1)),
                   cost_signpost=int(d.get("cost_signpost", 1)),
                   cost_clearing=int(d.get("cost_clearing", 1)))


# ---------------------------------------------------------------------------
# (De)serialization of parts (kind-tagged so the realizer can dispatch).
# ---------------------------------------------------------------------------
def _chain_to_dict(ch: Chain) -> dict:
    return {"head": ch.head, "hops": [list(h) for h in ch.hops]}


def _chain_from_dict(d: dict) -> Chain:
    return Chain(head=int(d["head"]), hops=tuple(tuple(int(x) for x in h) for h in d.get("hops", ())))


def _region_to_dict(r: Region) -> dict:
    if isinstance(r, Clearing):
        return {"kind": "clearing", "var": r.var, "Ld": r.Ld}
    return {"kind": "fork", "gate": r.gate, "Lv": r.Lv,
            "gate_hops": [list(h) for h in r.gate_hops],
            "chains": [_chain_to_dict(ch) for ch in r.chains]}


def _region_from_dict(d: dict) -> Region:
    if d.get("kind") == "clearing":
        return Clearing(var=int(d["var"]), Ld=int(d.get("Ld", 2)))
    return Fork(gate=int(d["gate"]), Lv=int(d.get("Lv", 9)),
                gate_hops=tuple(tuple(int(x) for x in h) for h in d.get("gate_hops", ())),
                chains=tuple(_chain_from_dict(c) for c in d["chains"]))


# ---------------------------------------------------------------------------
# Public cell descriptors — the cell layout WITHOUT hidden values, shared by world_map_public.
# ---------------------------------------------------------------------------
def public_cells(spec: WorldSpec) -> List[dict]:
    """Each cell as a PUBLIC descriptor: its cost, whether it is `probeable` / counts for `coverage`,
    and which `var` it reads (or `mirrors='target'` + its `region` if it is a fork's valley). The role
    falls out of those flags, so no narrative label is exposed."""
    out = []
    for i, c in enumerate(spec.cells()):
        entry = {"col": i, "cost": spec.cost_of(c),
                 "probeable": c[0] in ("sig", "direct"), "coverage": c[0] in ("direct", "valley")}
        if c[0] in ("sig", "direct"):
            entry["var"], entry["pos"] = c[1], c[2]
        else:
            entry["region"], entry["pos"], entry["mirrors"] = c[1], c[2], "target"
        out.append(entry)
    return out


# ---------------------------------------------------------------------------
# The deterministic expander: parts -> the tableau the grading engine consumes. Generic over the
# WorldSpec; the oracle/floor/screen in grade.py ride on its output and never look at the parts.
# ---------------------------------------------------------------------------
def build_tableau(spec: WorldSpec):
    """Rows = hypotheses (K**R variable assignments); columns = cells; plus the cost vector and two
    index sets that are the whole design:

      * `probe_cols` — what may be probed: the signposts (cheap pointers) and the clearing blocks. A
        valley is NOT probeable — it is inference-only, reconstructed by walking the trail.
      * `cov_cols` — what counts as coverage: the clearing blocks and the valleys. Signposts are NOT
        here — they are instruments. So walking a trail pays ZERO coverage until its valley flips on;
        no prefix pays, which is what makes the gap robust to a bounded planner."""
    cells = spec.cells()
    hyps = list(product(range(spec.K), repeat=spec.R))
    table = tuple(tuple(spec.cell_value(c, h) for c in cells) for h in hyps)
    costs = tuple(spec.cost_of(c) for c in cells)
    probe_cols = tuple(i for i, c in enumerate(cells) if c[0] in ("sig", "direct"))
    cov_cols = tuple(i for i, c in enumerate(cells) if c[0] in ("direct", "valley"))
    return table, cells, costs, cov_cols, probe_cols


# ---------------------------------------------------------------------------
# Validation: structural well-formedness BEFORE any oracle is derived. The integrity wall in code —
# a proposal is realized only if it is a legal structure, never because it claims a score.
# ---------------------------------------------------------------------------
def validate(spec: WorldSpec) -> List[str]:
    """Returns a list of problems (empty == ok). Checks ranges, K-length hop tables, the
    signpost/clearing disjointness, and that there is real bait off the trail."""
    issues: List[str] = []
    if spec.R < 2 or spec.K < 2:
        issues.append("need R>=2 and K>=2")
    if spec.Ls < 1:
        issues.append("signpost length Ls must be >= 1")
    if spec.budget < 1:
        issues.append("budget must be >= 1")
    regs = range(spec.R)

    def chk_hop(label, hop):
        if len(hop) != spec.K:
            issues.append(f"{label} must have length K={spec.K}")
        if any(r not in regs for r in hop):
            issues.append(f"{label} targets out of range")

    if not spec.forks() and not spec.clearing_regions():
        issues.append("no regions (need at least one clearing or fork)")
    for ri, r in enumerate(spec.regions):
        if isinstance(r, Clearing):
            if r.var not in regs:
                issues.append(f"region {ri} clearing var {r.var} out of range")
            if r.Ld < 1:
                issues.append(f"region {ri} clearing length Ld must be >= 1")
        else:
            if r.Lv < 1:
                issues.append(f"region {ri} valley length Lv must be >= 1")
            if r.n_chains < 1:
                issues.append(f"region {ri} fork needs at least one chain")
            if r.gate not in regs:
                issues.append(f"region {ri} gate {r.gate} out of range")
            for hi, hop in enumerate(r.gate_hops):
                chk_hop(f"region {ri} gate hop {hi}", hop)
            for ci, ch in enumerate(r.chains):
                if ch.head not in regs:
                    issues.append(f"region {ri} chain {ci} head {ch.head} out of range")
                for hi, hop in enumerate(ch.hops):
                    chk_hop(f"region {ri} chain {ci} hop {hi}", hop)
    sign = spec.signpost_vars()
    clear = set(spec.clearing_vars())
    if sign & clear:
        issues.append(f"variables {sorted(sign & clear)} are both signpost and clearing (must be disjoint)")
    if len(clear) != len(spec.clearing_vars()):
        issues.append("a variable carries more than one clearing block")
    if not clear:
        issues.append("no clearing variables (need immediate-coverage bait off the trail)")
    return issues
