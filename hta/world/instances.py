"""Named worlds, each authored as a parts-list in the world language (DESIGN.md §7: "author
instance 0 as a real parts-list in the language so it is the smith's worked example, not a
throwaway"). Every instance below is just a `WorldSpec` — disposable structure; the hidden seed is
drawn fresh per episode (`draw_hstar`), so a playbook must carry a method over, not memorize a case.

`instance0` is the proof-of-principle world: a single fork with a real gate and a deep valley plus
off-trail clearings. Unlike the retired flat allocation world (findings/2026-06-14), this is a
*position worth reading* — connected chains (depth), a valley that pays only end-to-end (compounding
access), a wrong chain that pins nothing (a dead end), and cheap gate/signpost reads (instruments).
The tasteful move it plants (never scripts): scout which chain is live before sinking budget into
depth. It is the decoy fork of `hta/_trail` re-expressed as composable parts, build-screened above
threshold (floor 4 -> oracle 11, gap ~0.71 of the band; see `run_lab.py screen`).
"""

import random
from typing import Tuple

from .language import Chain, Clearing, Fork, WorldSpec


def instance0() -> WorldSpec:
    """The proof-of-principle world (R=10, 1024 hypotheses, budget 4). ONE fork with TWO depth-2
    chains of equal public shape (so depth gives no tell) and a GATE (var 0) whose hidden value alone
    says which chain is live; the valley mirrors the LIVE chain's landmark. Budget 4 fits gate + one
    chain's walk (+ a clearing) but NOT both chains, so scarcity forces scout-then-commit. Three
    off-trail clearings (vars 7/8/9) are the immediate bait a lazy allocator grabs."""
    return WorldSpec(
        name="instance0", R=10, K=2, budget=4,
        regions=(
            Fork(gate=0, Lv=9,
                 chains=(Chain(head=1, hops=((2, 3),)),       # chain A: depth 2  (var1 -> {2,3})
                         Chain(head=4, hops=((5, 6),)))),     # chain B: depth 2  (var4 -> {5,6})
            Clearing(var=7), Clearing(var=8), Clearing(var=9)))


def ladder_world() -> WorldSpec:
    """A structurally HARDER world for the smith's ZPD move (R=12, 4096 hypotheses, budget 5): the
    fork's selector is an adaptive gate LADDER. Read the gate (var 0); its hidden value names which of
    {var 1, var 2} is the FINAL gate; only that gate's value selects the chain. The whole ladder is
    load-bearing, so reading only the first gate and committing leaves the valley unresolved whichever
    chain you walk. Distinct landmark pools ({6,7} vs {8,9}) keep all four candidate landmarks deep.
    The new disposition: scout the ladder step by step, THEN commit. (Screen: floor 5 -> oracle 11,
    gap ~0.83 of the band; lookahead-2 stalls at 6.)"""
    return WorldSpec(
        name="ladder", R=12, K=2, budget=5,
        regions=(
            Fork(gate=0, Lv=9, gate_hops=((1, 2),),           # gate0 -> final gate is var1 or var2
                 chains=(Chain(head=3, hops=((6, 7),)),       # chain A: depth 2  (var3 -> {6,7})
                         Chain(head=4, hops=((8, 9),)))),     # chain B: depth 2  (var4 -> {8,9})
            Clearing(var=5), Clearing(var=10), Clearing(var=11)))


def single_chain_world() -> WorldSpec:
    """The no-fork control: ONE depth-3 chain, so the gate carries no information and the valley is
    pinned by walking the single trail (exactly the anchor's policy). Above threshold like instance0
    (a depth-3 payoff a 2-step planner will not commit to under a tight budget), so a method that
    reaches the oracle here is doing real planning, not scouting a fork that is not there."""
    return WorldSpec(
        name="single-chain", R=9, K=2, budget=3,
        regions=(
            Fork(gate=0, Lv=9, chains=(Chain(head=1, hops=((2, 3), (4, 5))),)),  # var1->{2,3}->{4,5}
            Clearing(var=6), Clearing(var=7), Clearing(var=8)))


# The canonical world the first loop trains on (instance 0), exported for the loop/driver.
def canonical_spec() -> WorldSpec:
    return instance0()


def draw_hstar(spec: WorldSpec, seed: int) -> Tuple[int, ...]:
    """A fresh hidden world: a uniform draw of the K**R variable assignment (the only hidden
    information). Different seeds realize different shapes / live chains / trail ends, so the winning
    policy's CONTENT is learnable only by playing this instance, never read off the public structure."""
    rng = random.Random(seed)
    return tuple(rng.randrange(spec.K) for _ in range(spec.R))
