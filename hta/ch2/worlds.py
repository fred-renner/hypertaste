"""The world-smith's structural family — `ForkedTrailSpec`, the generalization of the anchor that
lets the **second loop** evolve the world's *structure* (ROADMAP.md -> "Closing the outer loop";
RESET_DESIGN.md -> the integrity wall lifted to the world-smith).

Where `anchor.TrailSpec` is a *single* trail (trailhead -> waypoint -> landmark -> valley) whose
optimal policy is "walk the trail, ignore the clearings", this is a **forked** trail: several
candidate chains plus a **gate** register whose hidden value selects which chain is *live* (carries
the valley). The anchor is the degenerate one-chain case. That one structural move — a gate that
*conditions the payoff on which chain you commit to* — is what no scalar dial of the anchor
produces (`run_probe.py` proved scalar cranks keep "walk the trail" optimal), and it demands a
*new* disposition: **scout which chain is feasible before sinking budget into depth.**

Why the champion fails it by strategy.  The anchor champion's grown note was "list every chain,
count payoff-per-dig, commit to the deepest." Here the valley mirrors the LIVE chain's landmark, and
*which* chain is live is the gate's hidden value — so to pin the valley you must pin the GATE (which
chain) **and** that chain's registers. Committing the budget to the deepest-looking chain WITHOUT
reading the cheap gate pins signposts that pay zero coverage and never resolves the valley, no matter
which chain you happened to walk. The cheap gate read is the feasibility scout; skipping it is the
strategy error. The optimal policy (read the gate, then commit to the live chain) reaches the oracle;
the champion's policy does not -> the structural ZPD gap (`world_smith.py` measures both, model-free).

Integrity wall (lifted to the second loop): the inventor proposes only this **structure** as
validated *data* (`to_dict`/`from_dict`/`validate` — safe-eval lifted, never code, never the score).
The referee (coverage) and the perfect-play benchmark (oracle) are re-derived **mechanically** by the
*unchanged*, structure-agnostic machinery in `anchor.py` (`build_tableau`/`oracle_value`/`screen`):
this spec only has to implement the same protocol the anchor does (`cells`, `cost_of`, `clearings`,
`trail_regs`, `landmark_reg`, K/R/Ld/Lv/budget), and the whole oracle/screen rides along for free.
"""

from dataclasses import dataclass
from typing import List, Tuple

from . import anchor


@dataclass(frozen=True)
class Chain:
    """One candidate trail: a `head` signpost register, then a sequence of public pointer `hops`.
    Walking it under a hypothesis (`ForkedTrailSpec.walk`) reads the head's hidden value to pick the
    next register, and so on, ending on a landmark register. Each hop is a length-K table mapping the
    current register's value -> the next register, so *which* register the chain ends on is the
    hidden seed (learnable only by playing), never readable off the public structure. Depth = 1 +
    len(hops)."""
    head: int
    hops: Tuple[Tuple[int, ...], ...]   # each hop: length-K table, current-reg-value -> next register

    @property
    def depth(self) -> int:
        return 1 + len(self.hops)


@dataclass(frozen=True)
class ForkedTrailSpec:
    """A forked B2 trail world. Public to everyone: the gate register, the candidate chains (their
    pointer tables), the clearing blocks, the costs, the budget. Hidden (the seed): the K**R register
    assignment, which fixes (a) which chain is live — `chains[final_gate_value % n_chains]`, the gate
    (or the gate ladder below) selecting it — and (b) where that chain ends. Two register roles,
    exactly as the anchor:

      * **signpost** registers (the gate + every register any chain can visit) are read through a
        cheap length-`Ls` cell that pays ZERO coverage — pure pointers / the feasibility gate.
      * **clearing** registers (everything else) carry a fat direct block of length `Ld` — a big
        immediate-coverage payoff for one probe, the off-trail bait.

    The valley (`Lv` cells) is inference-only: it mirrors the LIVE chain's landmark, so you
    reconstruct it by reading the gate then walking the live chain, never by drilling it.

    The gate can be a single register (the decoy) or an adaptive **ladder** of registers (`gate_hops`,
    the next structural move): with hops, you read the gate, its hidden value names the *next* gate to
    read, and so on -- the FINAL gate's value selects the live chain. The whole ladder is load-bearing
    (in `trail_regs`), so reading only the first gate leaves the valley unresolved no matter which
    chain you walk; the new disposition the ladder demands is **scout adaptively, then commit**.
    """
    name: str
    R: int                                  # registers (hidden values -> K**R hypotheses)
    K: int                                  # values per variable
    Ld: int                                 # clearing direct-block length (immediate bait)
    Lv: int                                 # valley length (the live chain's deep payoff)
    gate: int                               # the FIRST gate register (entry of the selector ladder)
    chains: Tuple[Chain, ...]               # >= 1 candidate chains; chains[final_gate_val % n] is live
    budget: int                             # scarce COST budget (probes draw from it, cost-weighted)
    gate_hops: Tuple[Tuple[int, ...], ...] = ()  # selector ladder: each hop maps the current gate's
                                            # value -> the next gate register (() == single-gate fork)
    Ls: int = 1                             # signpost cell length (a pointer, not payoff)
    cost_signpost: int = 1                  # cost to read a signpost / a gate (the cheap door)
    cost_clearing: int = 1                  # cost to probe a clearing block (variable-cost knob)

    # ---- the trail topology (the protocol anchor.py's oracle/screen consume) ----
    @property
    def n_chains(self) -> int:
        return len(self.chains)

    def gate_chain(self, hyp: Tuple[int, ...]) -> List[int]:
        """The gate registers the selector ladder visits under `hyp` (the first gate, then each
        gate-hop's target). The LAST is the FINAL gate, whose value selects the live chain. With no
        `gate_hops` this is just `[gate]` — the single-gate fork (the decoy). Like `walk`, it is
        data-dependent: which gate you read next is the hidden content, so the ladder cannot be
        pre-listed off the public structure — you must scout it step by step."""
        r = self.gate
        visited = [r]
        for hop in self.gate_hops:
            r = hop[hyp[r] % self.K]
            visited.append(r)
        return visited

    def final_gate(self, hyp: Tuple[int, ...]) -> int:
        return self.gate_chain(hyp)[-1]

    def walk(self, chain: Chain, hyp: Tuple[int, ...]) -> List[int]:
        """The registers this chain visits under `hyp` (head, then each hop's target). The last is
        the landmark. Data-dependent: that is the hidden content."""
        r = chain.head
        visited = [r]
        for hop in chain.hops:
            r = hop[hyp[r] % self.K]
            visited.append(r)
        return visited

    def live_index(self, hyp: Tuple[int, ...]) -> int:
        return hyp[self.final_gate(hyp)] % self.n_chains

    def landmark_reg(self, hyp: Tuple[int, ...]) -> int:
        """The LIVE chain's landmark — the register the valley mirrors. Selected by the gate ladder's
        FINAL gate (`chains[final_gate_value % n_chains]`) then walked to its end. (Same name as
        `TrailSpec.landmark_reg` so the module-level `cell_value`/oracle stay structure-agnostic.)"""
        return self.walk(self.chains[self.live_index(hyp)], hyp)[-1]

    def trail_regs(self, hyp: Tuple[int, ...]) -> Tuple[int, ...]:
        """The registers that must ALL be pinned before the valley flips on: every register the live
        chain visits, PLUS the whole GATE LADDER iff there is a real fork (n_chains > 1) — with a
        single chain the gate selects nothing, so it is not load-bearing. Walking the wrong chain, or
        reading only the first gate of the ladder, pins none of the rest, which is why skipping the
        adaptive scout loses the valley."""
        visited = self.walk(self.chains[self.live_index(hyp)], hyp)
        head = self.gate_chain(hyp) if self.n_chains > 1 else []
        return tuple(dict.fromkeys([*head, *visited]))

    def signposts(self) -> Tuple[int, ...]:
        """Every register read as a cheap pointer: the gate ladder (the gate + every gate-hop target)
        + every register any chain can visit (heads and all hop targets). Auto-derived so the layout
        and the cells stay in lockstep."""
        regs = {self.gate}
        for hop in self.gate_hops:
            regs.update(hop)
        for ch in self.chains:
            regs.add(ch.head)
            for hop in ch.hops:
                regs.update(hop)
        return tuple(sorted(regs))

    def clearings(self) -> Tuple[int, ...]:
        sign = set(self.signposts())
        return tuple(i for i in range(self.R) if i not in sign)

    def cells(self) -> List[Tuple]:
        """Column layout (descriptors; values are per-hypothesis): cheap signpost cells, fat clearing
        blocks, then the (single) valley — identical kinds to the anchor, so `build_tableau`'s
        probe/coverage column rules apply unchanged."""
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

    # ---- the public face (delegated to by episode_state.world_map through the unchanged airgap) ----
    def world_map_public(self, remaining: int) -> dict:
        ladder = (
            "" if not self.gate_hops else
            " The gate is an adaptive LADDER: read the gate, its hidden value names the NEXT gate to "
            "read (gate_hops[value]), and so on to the FINAL gate — only the final gate's value "
            "selects the chain, so reading only the first gate is not enough; you must scout the "
            "ladder step by step.")
        value_rule = (
            "Cell values are a deterministic lookup, never a pattern to guess: a cell's value = "
            "(its variable's hidden value + pos) mod K. A cell with a `var` field uses that "
            "variable. A cell marked mirrors='target' uses the LIVE chain's TARGET variable: the "
            "FINAL gate variable's hidden value selects which chain is live (final_gate_value mod "
            "n_chains), and you walk that chain's pointer hops to its target." + ladder +
            " So to reconstruct those cells you must pin the GATE LADDER (which chain is live) AND that "
            "chain's variables (its target value) — walking the wrong chain, or skipping any gate, "
            "pins nothing of them. Once a variable's value is pinned, every cell keyed to it is "
            "fully determined.")
        return {"R": self.R, "K": self.K, "budget": self.budget, "remaining": remaining,
                "n_chains": self.n_chains, "value_rule": value_rule,
                "fork": {"gate": self.gate, "gate_hops": [list(h) for h in self.gate_hops],
                         "selects": "chains[final_gate_value % n_chains] is the LIVE chain; the final "
                                    "gate is reached by walking the gate ladder (gate, then gate_hops)",
                         "chains": [{"head": ch.head, "hops": [list(h) for h in ch.hops]}
                                    for ch in self.chains]},
                "cells": anchor.public_cells(self)}

    def report_blurb(self) -> str:
        """One-line PUBLIC description for the sanitized meta/inventor report (no hidden values)."""
        shapes = "; ".join(f"chain {i} (head {ch.head}, depth {ch.depth})" for i, ch in enumerate(self.chains))
        gate_desc = (f"a GATE (reg {self.gate})" if not self.gate_hops else
                     f"an adaptive GATE LADDER (gate reg {self.gate}, hops {[list(h) for h in self.gate_hops]}, "
                     f"each hop's value naming the next gate to read)")
        return (f"a FORKED trail through {self.R} registers: {self.n_chains} candidate chains [{shapes}] "
                f"and {gate_desc} whose hidden value(s) select which chain is LIVE "
                f"(chains[final_gate_value % {self.n_chains}]); the deep valley mirrors the LIVE chain's "
                f"landmark, so it pays only once you scout the gate(s) AND walk that chain. Reading a "
                f"signpost (incl. any gate) pays ZERO coverage; the clearing blocks pay immediately")

    # ---- declarative (de)serialization: the inventor proposes/realizes STRUCTURE as data ----
    def to_dict(self) -> dict:
        return {"kind": "forked", "name": self.name, "R": self.R, "K": self.K, "Ld": self.Ld,
                "Lv": self.Lv, "gate": self.gate,
                "chains": [{"head": ch.head, "hops": [list(h) for h in ch.hops]} for ch in self.chains],
                "budget": self.budget, "gate_hops": [list(h) for h in self.gate_hops], "Ls": self.Ls,
                "cost_signpost": self.cost_signpost, "cost_clearing": self.cost_clearing}

    @classmethod
    def from_dict(cls, d: dict) -> "ForkedTrailSpec":
        chains = tuple(Chain(head=int(c["head"]), hops=tuple(tuple(int(x) for x in h) for h in c["hops"]))
                       for c in d["chains"])
        gate_hops = tuple(tuple(int(x) for x in h) for h in d.get("gate_hops", ()))
        return cls(name=d["name"], R=int(d["R"]), K=int(d["K"]), Ld=int(d["Ld"]), Lv=int(d["Lv"]),
                   gate=int(d["gate"]), chains=chains, budget=int(d["budget"]), gate_hops=gate_hops,
                   Ls=int(d.get("Ls", 1)), cost_signpost=int(d.get("cost_signpost", 1)),
                   cost_clearing=int(d.get("cost_clearing", 1)))


def validate(spec: ForkedTrailSpec) -> List[str]:
    """Structural well-formedness of an inventor-proposed world (BEFORE any oracle is derived from
    it). The integrity wall in code: a proposal is realized only if it is a legal structure — never
    because it claims a score. Returns a list of problems (empty == ok)."""
    issues: List[str] = []
    if spec.R < 2 or spec.K < 2:
        issues.append("need R>=2 and K>=2")
    if spec.Lv < 1 or spec.Ld < 1 or spec.Ls < 1:
        issues.append("block lengths Lv/Ld/Ls must be >= 1")
    if spec.n_chains < 1:
        issues.append("need at least one chain")
    regs = list(range(spec.R))
    if spec.gate not in regs:
        issues.append(f"gate {spec.gate} out of range")
    for hi, hop in enumerate(spec.gate_hops):
        if len(hop) != spec.K:
            issues.append(f"gate hop {hi} must have length K={spec.K}")
        if any(r not in regs for r in hop):
            issues.append(f"gate hop {hi} targets out of range")
    for ci, ch in enumerate(spec.chains):
        if ch.head not in regs:
            issues.append(f"chain {ci} head {ch.head} out of range")
        for hi, hop in enumerate(ch.hops):
            if len(hop) != spec.K:
                issues.append(f"chain {ci} hop {hi} must have length K={spec.K}")
            if any(r not in regs for r in hop):
                issues.append(f"chain {ci} hop {hi} targets out of range")
    if not spec.clearings():
        issues.append("no clearing registers (need immediate-coverage bait off the trail)")
    if spec.budget < 1:
        issues.append("budget must be >= 1")
    return issues


# ---------------------------------------------------------------------------
# Concrete worlds. `single_chain_*` is the anchor-equivalent control (a fork with one chain, so the
# gate is degenerate and "walk the trail" still wins). `decoy_*` is the world-smith's first
# structurally-harder world (two chains + a meaningful gate -> scout-then-commit).
# ---------------------------------------------------------------------------
def single_chain_spec() -> ForkedTrailSpec:
    """The no-fork control: ONE depth-3 chain, so `gate_value % 1 == 0` always selects it — the gate
    carries no information and the valley is pinned by walking the single trail, exactly the anchor's
    policy. Above threshold like the anchor (a depth-3 payoff a 2-step planner won't commit to under a
    tight budget), so the champion's rule ("walk the trail, reconstruct the valley") reaching the
    oracle HERE is meaningful: with no fork to scout, blind commitment is correct. R=9 -> regs 6/7/8
    are the three clearings; budget 3 (tight, like the anchor) keeps it above threshold."""
    return ForkedTrailSpec(
        name="forked-single", R=9, K=2, Ld=2, Lv=9, gate=0,
        chains=(Chain(head=1, hops=((2, 3), (4, 5))),), budget=3)  # depth-3: reg1 -> {2,3} -> {4,5}


def decoy_spec() -> ForkedTrailSpec:
    """The world-smith's first structurally-harder world (R=10, 1024 hyps, budget 4). TWO candidate
    chains of equal public shape (so depth gives no tell — the champion's "commit to the deepest"
    heuristic has no purchase) and a GATE (reg 0) whose hidden value alone says which chain is live.
    The valley mirrors the LIVE chain's landmark, so to pin it you must read the gate AND walk that
    chain. Budget 4 fits gate + one chain's walk (+ a clearing), but NOT both chains — scarcity forces
    scout-then-commit. Committing to a chain without the cheap gate scout pins zero valley, whichever
    chain it is: the structural strategy-trap. (Screen: floor 4 -> oracle 11, gap 0.71n, heur 0.29n —
    above threshold with live-student room.)"""
    return ForkedTrailSpec(
        name="decoy", R=10, K=2, Ld=2, Lv=9, gate=0,
        chains=(Chain(head=1, hops=((2, 3),)),            # chain A: depth 2  (reg1 -> {2,3})
                Chain(head=4, hops=((5, 6),))),           # chain B: depth 2  (reg4 -> {5,6})
        budget=4)


def ladder_spec() -> ForkedTrailSpec:
    """The world-smith's SECOND structural move — the adaptive **gate ladder** (R=12, 4096 hyps,
    budget 5). The decoy taught "scout THE gate, then commit"; this breaks that one level up: the live
    chain is selected not by one gate but by a *ladder* of gates — read the gate (reg 0), its hidden
    value names which of {reg 1, reg 2} is the FINAL gate, and only that gate's value selects the chain.
    The whole ladder is load-bearing (in `trail_regs`), so a player that reads only the first gate and
    commits (the decoy champion's grown rule) leaves the valley unresolved DETERMINISTICALLY, whichever
    chain it walks — the strategy-trap, lifted to an adaptive scout. The new disposition: scout the
    ladder step by step (each gate names the next), THEN commit to the live chain and walk it.

    Deeper AND adaptive: depth-2 chains with DISTINCT landmark pools ({6,7} vs {8,9}, so the four
    candidate landmarks stay deep — no cheap "read both and hope they agree" shortcut) under the
    depth-2 ladder -> a 4-deep live trail (gate -> final gate -> chain head -> chain hop), versus the
    decoy's 3. Budget 5 co-evolves with the world but stays tight: it fits the ladder (2) + one chain's
    walk (2) + a clearing (1), but not a blind sweep. (Screen: floor 5 -> oracle 11, gap 0.83n, heur
    0.17n; lookahead-2 stalls at 6 — above threshold with live-student room. See run_worldsmith.py.
    The exact oracle over 4096 hypotheses is the costly part; it is computed once per run and is the
    same reference the live episodes are scored against.)"""
    return ForkedTrailSpec(
        name="ladder", R=12, K=2, Ld=2, Lv=9, gate=0,
        gate_hops=((1, 2),),                              # gate reg0 -> final gate is reg1 or reg2
        chains=(Chain(head=3, hops=((6, 7),)),            # chain A: depth 2  (reg3 -> {6,7})
                Chain(head=4, hops=((8, 9),))),           # chain B: depth 2  (reg4 -> {8,9})
        budget=5)                                          # clearings: regs 5, 10, 11
