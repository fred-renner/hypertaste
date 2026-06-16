"""World-smith tests — the second loop's ship-gate + inventor scaffold (`hta/_trail/world_smith.py`).
Deterministic, pure compute, no API cost.

The load-bearing claims:
- The champion's articulable method (commit-to-the-deepest) reaches the oracle on a NON-forked world
  but collapses to the floor on a fork — the structural strategy-trap, measured model-free.
- The fix (scout-then-commit) reaches the oracle band on both: the harder world is SOLVABLE by the
  right method, so the gap is the ZPD (fail-now-but-learnable), not an impossible wall.
- The ship-gate ships a world ONLY if it is hard + solvable + the champion fails (the only legal
  coupling is the objective gap on the non-movable scorer). A world the champion already solves does
  not ship.
- The inventor proposes STRUCTURE as data (safe-eval lifted): `realize_proposal` builds + validates a
  spec from JSON and rejects malformed proposals; it never executes the proposal.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta._trail import world_smith as ws  # noqa: E402
from hta._trail.worlds import Chain, ForkedTrailSpec, decoy_spec, single_chain_spec  # noqa: E402

# A small HARD fork (512 hypotheses, budget 3): two depth-2 chains + a gate, enough clearings (regs
# 6/7/8) that the gap holds — fast enough for the suite while still shipping.
FORK = ForkedTrailSpec("fork-zpd", R=9, K=2, Ld=2, Lv=9, gate=0,
                       chains=(Chain(1, ((2, 3),)), Chain(4, ((5, 6),))), budget=3)
# A small LADDER fork (512 hypotheses, budget 5): iteration 2's move scaled down — a depth-2 gate
# ladder (gate reg0 -> final gate reg1 or reg2) over two chains. The iteration-1 graduate's rule
# (scout THE gate, then commit) reads only the first gate and fails; the adaptive scout solves it.
LADDER = ForkedTrailSpec("ladder-zpd", R=9, K=2, Ld=2, Lv=9, gate=0, gate_hops=((1, 2),),
                         chains=(Chain(3, ((6, 7),)), Chain(4, ((7, 6),))), budget=5)


def test_champion_method_fails_on_a_fork_but_wins_without_one():
    # Same articulable method, opposite outcomes: the FORK is what breaks "commit to the deepest".
    fork_norm, _ = ws.policy_band(FORK, ws.commit_deepest)
    single_norm, _ = ws.policy_band(single_chain_spec(), ws.commit_deepest)
    assert fork_norm <= ws.FAIL_BAR          # stalls near the floor on the fork
    assert single_norm >= ws.SOLVE_BAR       # reaches the oracle with no fork to scout


def test_fix_reaches_the_oracle_on_the_fork():
    # The world is solvable by the right method -> the gap is learnable (the ZPD), not a wall.
    fix_norm, _ = ws.policy_band(FORK, ws.scout_then_commit)
    assert fix_norm >= ws.SOLVE_BAR


def test_ship_gate_ships_a_fork_and_holds_an_already_solved_world():
    forked = ws.ship_gate(FORK)
    assert forked["hard"] and forked["solvable"] and forked["champion_fails"] and forked["ship"]
    # the no-fork control is hard too, but the champion already wins it -> not in the ZPD -> hold
    control = ws.ship_gate(single_chain_spec())
    assert not control["champion_fails"] and not control["ship"]


def test_ship_requires_the_champion_to_fail_the_zpd_coupling():
    # The only legal coupling is the objective gap: a hard+solvable world the champion already solves
    # must NOT ship (designing around a non-existent weakness would be Goodhart at the curriculum level).
    g = ws.ship_gate(single_chain_spec())
    assert g["hard"] and g["solvable"]
    assert not g["champion_fails"]
    assert not g["ship"]


def test_propose_move_is_shippable():
    assert ws.ship_gate(ws.propose_move())["ship"]


def test_gate_ladder_breaks_scout_the_first_gate_but_the_adaptive_scout_solves_it():
    # Iteration 2's ZPD, one rung up: the decoy's FIX (scout THE gate, then commit) becomes the
    # ladder's CHAMPION — it reads only the first gate, leaves the rest of the ladder unpinned, and
    # stalls at the floor; the adaptive scout (walk the whole ladder, then commit) reaches the oracle.
    champ_norm, _ = ws.policy_band(LADDER, ws.scout_then_commit)
    fix_norm, _ = ws.policy_band(LADDER, ws.scout_ladder_then_commit)
    assert champ_norm <= ws.FAIL_BAR
    assert fix_norm >= ws.SOLVE_BAR


def test_ship_gate_takes_the_champion_and_fix_methods_of_the_move():
    # The move carries WHICH rule it must break and WHICH closes it. The ladder ships against the
    # iteration-1 graduate (scout_then_commit) with the adaptive scout as the fix.
    g = ws.ship_gate(LADDER, champion_method=ws.scout_then_commit,
                     fix_method=ws.scout_ladder_then_commit)
    assert g["hard"] and g["solvable"] and g["champion_fails"] and g["ship"]
    # the decoy's fix is exactly the degenerate (zero-rung) adaptive scout, so on the single-gate
    # decoy the two fix methods agree — the ladder logic generalizes scout-then-commit, not replaces it
    d_then, _ = ws.policy_band(decoy_spec(), ws.scout_then_commit)
    d_ladder, _ = ws.policy_band(decoy_spec(), ws.scout_ladder_then_commit)
    assert d_then == d_ladder >= ws.SOLVE_BAR


def test_curriculum_carries_the_graduate_forward_as_the_next_champion():
    # The outer loop closing on itself: move 1's FIX is move 2's CHAMPION (the coached player carries
    # forward), and each move declares a distinct harder world.
    moves = ws.CURRICULUM
    assert len(moves) == 2
    assert moves[0]["fix"] is moves[1]["champion"]
    assert moves[0]["spec"]().name != moves[1]["spec"]().name
    assert moves[0]["child_name"] != moves[1]["child_name"]


def test_realize_proposal_builds_validated_structure_from_data():
    import json
    proposal = "Here is the world:\n" + json.dumps(decoy_spec().to_dict()) + "\nThanks."
    spec, issues = ws.realize_proposal(proposal)
    assert issues == [] and spec == decoy_spec()


def test_realize_proposal_rejects_malformed_and_non_json():
    spec, issues = ws.realize_proposal("no json here, just prose")
    assert spec is None and issues
    bad = '{"kind":"forked","name":"x","R":8,"K":2,"Ld":2,"Lv":9,"gate":99,' \
          '"chains":[{"head":1,"hops":[[2,3]]}],"budget":3}'   # gate out of range
    spec, issues = ws.realize_proposal(bad)
    assert spec is not None and any("gate" in m for m in issues)   # realized, but flagged invalid
