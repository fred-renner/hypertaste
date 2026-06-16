"""World-smith tests (hta/gym/smith.py) — the ship-gate (the ZPD coupling) and the safe-eval inventor
realizer. Deterministic, offline, no API cost.

The load-bearing claims:
- The ship-gate's ZPD coupling: on a FORK world the champion's depth-committing rule FAILS (stalls at
  the floor) while the scout-then-commit fix REACHES the oracle band — and the world is still hard +
  solvable, so it SHIPS. The only coupling to the agent is this objective gap on the non-movable
  scorer.
- One level up, on a gate LADDER, scout-THE-gate becomes the failing champion and scout-the-ladder
  the fix (the decoy's graduate is the ladder's champion) — the outer loop closing on itself.
- A no-fork control does NOT ship (no champion failure to exploit).
- The inventor proposes STRUCTURE as data: a well-formed parts-list realizes; a malformed/illegal one
  is rejected with issues, never executed (safe-eval lifted).

Small worlds (256 hypotheses) keep the belief-MDP oracle fast; the canonical instance0/ladder bands
are checked in run_lab.py / test_world_grade.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.gym import smith  # noqa: E402
from hta.world.instances import instance0, single_chain_world  # noqa: E402
from hta.world.language import Chain, Clearing, Fork, WorldSpec  # noqa: E402

# The above-threshold gate needs enough off-trail bait, so these are R=9-10 (512-1024 hyps; the
# belief-MDP oracle is cached per spec). DECOY is the canonical instance0; LADDER is a fast R=10
# depth-2 gate ladder; SINGLE is the no-fork control. (The R=12 canonical ladder is exercised in
# run_lab.py, not the unit suite, to keep the default tests quick.)
DECOY = instance0()
LADDER = WorldSpec("ladder-r10", R=10, K=2, budget=5, regions=(
    Fork(gate=0, Lv=9, gate_hops=((1, 2),), chains=(Chain(3, ((5, 6),)), Chain(4, ((5, 6),)))),
    Clearing(7), Clearing(8), Clearing(9)))
SINGLE = single_chain_world()


def test_decoy_ships_champion_fails_fix_succeeds():
    g = smith.ship_gate(DECOY, smith.commit_deepest, smith.scout_then_commit)
    assert g["champion_fails"] and g["champion_norm"] <= smith.FAIL_BAR
    assert g["fix_norm"] >= smith.SOLVE_BAR
    assert g["hard"] and g["solvable"] and g["ship"]


def test_ladder_ships_scout_the_gate_now_fails_scout_the_ladder_fixes():
    g = smith.ship_gate(LADDER, smith.scout_then_commit, smith.scout_ladder_then_commit)
    assert g["champion_fails"]                                   # one scout is no longer enough
    assert g["fix_norm"] >= smith.SOLVE_BAR and g["ship"]


def test_no_fork_control_does_not_ship():
    # A single-chain world is hard (a depth-3 commitment), but the depth-committing champion REACHES
    # the oracle here (there is no fork to scout) -> no champion failure -> it must not ship.
    g = smith.ship_gate(SINGLE, smith.commit_deepest, smith.scout_then_commit)
    assert not g["champion_fails"] and not g["ship"]


def test_realize_proposal_round_trips_valid_structure():
    proposal = '{"R": 8, "K": 2, "budget": 4, "regions": [' \
               '{"kind": "fork", "gate": 0, "Lv": 9, "chains": [' \
               '{"head": 1, "hops": [[2, 3]]}, {"head": 4, "hops": [[5, 6]]}]},' \
               '{"kind": "clearing", "var": 7, "Ld": 2}]}'
    spec, issues = smith.realize_proposal(proposal)
    assert issues == [] and spec is not None
    assert spec.R == 8 and len(spec.forks()) == 1 and spec.forks()[0].n_chains == 2


def test_realize_proposal_rejects_malformed_and_illegal():
    spec, issues = smith.realize_proposal("not json at all")
    assert spec is None and issues
    # well-formed JSON but an illegal structure (gate out of range, no clearing) -> validation issues
    bad = '{"R": 3, "K": 2, "budget": 2, "regions": [' \
          '{"kind": "fork", "gate": 9, "Lv": 9, "chains": [{"head": 1, "hops": [[2, 0]]}]}]}'
    spec2, issues2 = smith.realize_proposal(bad)
    assert spec2 is None and any("out of range" in m for m in issues2)
