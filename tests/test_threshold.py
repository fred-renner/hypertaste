"""Threshold-screen tests (deterministic, pure compute, no API cost).

Verify the gate that decides whether a Chapter-2 world can earn the loop's keep
(ROADMAP -> "earning its keep"): the belief-MDP oracle, the articulable basket, and the
separation of an independent (below-threshold) world from a coupled stepping-stone (above).

The load-bearing claims:
- The reference ordering holds always: floor <= heuristic <= oracle <= clairvoyant.
- An INDEPENDENT register world is BELOW threshold: the best articulable heuristic == the
  oracle (the optimal policy is greedy = a closed form), so any taste-gap there is noise.
- A coupled STEPPING-STONE world is ABOVE threshold: the oracle strictly beats every
  articulable policy in the basket INCLUDING a 2-step lookahead planner -> the optimal policy
  needs deeper-than-bounded planning, i.e. it is genuinely not closed-form (the verdict is
  robust to 'the basket was just weak').
- The substrate stays a dumb deterministic f(structure, observations) and the oracle is exact
  but token-free — computable yet not expressible, which is what keeps it affordable.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.ch2.threshold import (  # noqa: E402
    LinkSpec, build_tableau, clairvoyant_value, determined, lookahead_value,
    oracle_value, ramp_curve, screen,
)

# The control (independent, all-direct = the tape's structure) and the recommended starting
# world (a lure anchor + a buried triangle of hidden registers) from `run_threshold.py`.
CONTROL = LinkSpec("control", R=3, K=3, Ld=2, Ll=2, edges=(), budget=2, direct=(0, 1, 2))
TRAP = LinkSpec("trap-tri", R=4, K=3, Ld=2, Ll=2,
                edges=((1, 2), (1, 3), (2, 3)), budget=3, direct=(0,))


def test_expander_deterministic_and_bounded():
    table, cells = build_tableau(TRAP)
    assert len(table) == TRAP.K ** TRAP.R            # one row per hypothesis
    assert all(len(row) == TRAP.M for row in table)  # one column per cell
    assert all(0 <= v < TRAP.K for row in table for v in row)
    assert build_tableau(TRAP)[0] == table           # deterministic


def test_reference_ordering_holds():
    # floor <= best heuristic <= oracle <= clairvoyant, on both worlds.
    for spec in (CONTROL, TRAP):
        s = screen(spec)
        assert s["floor"] <= s["best_heur"] <= s["oracle"] <= s["clairvoyant"] + 1e-9
        # the belief-MDP oracle dominates every articulable policy individually
        assert all(s["oracle"] >= h - 1e-9 for h in s["heurs"].values())


def test_independent_world_is_below_threshold():
    # No coupling -> coverage is adaptive-submodular -> greedy is optimal -> the best
    # articulable heuristic matches the oracle exactly. A taste-gap here would be noise.
    s = screen(CONTROL)
    assert abs(s["oracle"] - s["best_heur"]) < 1e-9
    assert s["gap_norm"] < 1e-9
    assert s["ramp_r2"] > 0.999  # R^2 == 1.0 is the signature of an independent world


def test_stepping_stone_world_is_above_threshold():
    # Coupling (edges over hidden registers) makes value-of-information non-submodular: the
    # oracle STRICTLY beats every articulable policy, including the 2-step planner.
    s = screen(TRAP)
    assert s["oracle"] > s["best_heur"] + 1e-9
    assert s["gap_norm"] >= 0.15
    assert s["heurs"]["lookahead2"] < s["oracle"] - 1e-9  # needs deeper than 2-step planning


def test_uncertainty_is_not_the_gap():
    # clairvoyant == oracle on the trap: the gap is NOT the price of not knowing the world
    # (that would be trivially articulable as "probe what you don't know"), it is the price of
    # the optimal *policy* having no closed form. This is the threshold proper.
    s = screen(TRAP)
    assert abs(s["clairvoyant"] - s["oracle"]) < 1e-9


def test_full_lookahead_converges_to_oracle():
    # The bounded planner at depth == budget IS the full belief-MDP; sanity that the basket's
    # strongest member is a faithful truncation (so the depth-2 shortfall is real, not a bug).
    assert abs(lookahead_value(TRAP, depth=TRAP.budget) - oracle_value(TRAP)) < 1e-9


def test_oracle_is_budget_monotone():
    # More probes can never determine fewer cells (a sanity check on the value iteration).
    vals = [oracle_value(TRAP, budget=b) for b in range(TRAP.budget + 1)]
    assert all(b >= a - 1e-9 for a, b in zip(vals, vals[1:]))


def test_ramp_is_monotone_and_anti_cliff():
    # bet 2 for a coupled world: partial inference buys proportional coverage with no
    # all-or-nothing jump (monotone, no step carries the whole coverage).
    curve = ramp_curve(TRAP)
    steps = [b - a for a, b in zip(curve, curve[1:])]
    assert all(d > -1e-9 for d in steps)   # monotone
    assert max(steps) <= 0.55              # anti-cliff (not [0,0,0,1])
    assert curve[0] == 0.0 and abs(curve[-1] - 1.0) < 1e-9


def test_determined_is_agent_inaccessible_and_exact():
    # Coverage is a dumb deterministic function of the consistent hypothesis set: full set ->
    # nothing pinned; singleton -> everything pinned. No LLM, unmovable by the agent.
    table, cells = build_tableau(TRAP)
    cols = tuple(range(len(cells)))
    H_all = frozenset(range(len(table)))
    assert determined(table, cols, H_all) == 0            # nothing determined a priori
    assert determined(table, cols, frozenset({0})) == TRAP.M  # one world -> all cells pinned
