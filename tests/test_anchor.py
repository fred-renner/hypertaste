"""Anchor-family (B2 trail world) build-screen tests — deterministic, pure compute, no API cost.

Verify the gate that decides whether the Chapter-2 *allocation* world can earn the loop's keep
(RESET_DESIGN.md -> "The world design"): the cost-weighted belief-MDP oracle, the articulable
basket, and the separation of a below-threshold control from the trail-gated valley.

The load-bearing claims (the B2 analogue of `test_threshold.py`):
- The reference ordering holds always: floor <= best heuristic <= oracle <= clairvoyant.
- Reconstruction is a LOOKUP, not a solve (B2): pinning the three trail registers determines the
  whole valley; the valley is never probed.
- A world with no deep payoff (or a slack budget) is BELOW threshold: greedy == the oracle, so any
  taste-gap is noise.
- The trail is ABOVE threshold: the oracle strictly beats every articulable policy INCLUDING the
  2-step planner -> the optimal allocation needs deeper-than-bounded planning (robust to "the
  basket was just weak"), and the win comes from allocation depth, not hard inference.
- The substrate stays a dumb deterministic f(structure, observations); the oracle is exact but
  token-free.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.ch2.anchor import (  # noqa: E402
    TrailSpec, build_tableau, determined, lookahead_value, oracle_value, ramp_curve, screen,
)

# A small, fast trail (256 hypotheses): trailhead -> waypoint(1|2) -> landmark(3|4), three clearing blocks, valley
# of 9 reconstructed cells, budget 3. The canonical run-pick (run_anchor.py) is the same shape,
# larger (Lv=9, R=10); kept small here so the suite stays a couple of seconds.
TRAIL = TrailSpec("trail-small", R=8, K=2, Ld=2, Lv=9, trailhead=0,
                  waypoints=(1, 2), landmarks=((3, 4), (3, 4)), budget=3)
CONTROL = TrailSpec("ctrl-novalley", R=8, K=2, Ld=2, Lv=0, trailhead=0,
                    waypoints=(1, 2), landmarks=((3, 4), (3, 4)), budget=3)


def test_expander_deterministic_and_bounded():
    table, cells, costs, cov, probe = build_tableau(TRAIL)
    assert len(table) == TRAIL.K ** TRAIL.R              # one row per hypothesis
    assert all(len(row) == TRAIL.M for row in table)     # one column per cell
    assert all(0 <= v < TRAIL.K for row in table for v in row)
    assert build_tableau(TRAIL)[0] == table              # deterministic
    # the valley is inference-only: every valley column is scored as coverage but never probeable
    valley_cols = [i for i, c in enumerate(cells) if c[0] == "valley"]
    assert valley_cols and all(i in cov and i not in probe for i in valley_cols)
    # signposts are instruments: probeable but NOT coverage
    sig_cols = [i for i, c in enumerate(cells) if c[0] == "sig"]
    assert sig_cols and all(i in probe and i not in cov for i in sig_cols)


def test_reconstruction_is_a_lookup_not_a_solve():
    # B2: once the three trail registers (trailhead, waypoint, landmark) are pinned, the whole valley is
    # determined by consensus — no joint solve, the deep payoff is a lookup. Pin them for one true
    # world and check every valley cell is determined.
    table, cells, costs, cov, probe = build_tableau(TRAIL)
    import itertools
    hyps = list(itertools.product(range(TRAIL.K), repeat=TRAIL.R))
    h = hyps[0]
    trail = TRAIL.trail_regs(h)
    assert len(trail) == 3                               # depth-3 trail (trailhead, waypoint, landmark)
    H = frozenset(i for i, hh in enumerate(hyps) if all(hh[r] == h[r] for r in trail))
    valley_cols = tuple(i for i, c in enumerate(cells) if c[0] == "valley")
    assert determined(table, valley_cols, H) == TRAIL.Lv  # all Lv valley cells pinned by the trail
    # ...and pinning only two of the three leaves the valley unresolved (non-submodular, deep)
    H2 = frozenset(i for i, hh in enumerate(hyps) if all(hh[r] == h[r] for r in trail[:2]))
    assert determined(table, valley_cols, H2) == 0


def test_reference_ordering_holds():
    for spec in (CONTROL, TRAIL):
        s = screen(spec)
        assert s["floor"] <= s["best_heur"] <= s["oracle"] <= s["clairvoyant"] + 1e-9
        assert all(s["oracle"] >= h - 1e-9 for h in s["heurs"].values())


def test_control_is_below_threshold():
    # No deep payoff -> coverage is just the clearing blocks -> greedy is optimal -> the best
    # articulable heuristic matches the oracle. A taste-gap here would be noise.
    s = screen(CONTROL)
    assert abs(s["oracle"] - s["best_heur"]) < 1e-9
    assert s["gap_norm"] < 1e-9
    assert s["ramp_r2"] > 0.999  # R^2 == 1.0: pure linear clearing mass, the independent-world signature


def test_trail_is_above_threshold():
    # The trail-gated payoff under deception makes the optimal allocation non-shallow: the oracle
    # STRICTLY beats every articulable policy, including the 2-step planner.
    s = screen(TRAIL)
    assert s["oracle"] > s["best_heur"] + 1e-9
    assert s["gap_norm"] >= 0.15
    assert s["heurs"]["lookahead2"] < s["oracle"] - 1e-9  # needs deeper than 2-step planning


def test_full_lookahead_converges_to_oracle():
    # The bounded planner at depth == budget IS the full belief-MDP: sanity that the basket's
    # strongest member is a faithful truncation, so the depth-2 shortfall is real, not a bug.
    assert abs(lookahead_value(TRAIL, depth=TRAIL.budget) - oracle_value(TRAIL)) < 1e-9


def test_oracle_is_budget_monotone():
    vals = [oracle_value(TRAIL, budget=b) for b in range(TRAIL.budget + 1)]
    assert all(b >= a - 1e-9 for a, b in zip(vals, vals[1:]))


def test_ramp_is_monotone_and_anti_cliff():
    # bet 2: partial inference buys proportional coverage with no all-or-nothing jump.
    curve = ramp_curve(TRAIL)
    steps = [b - a for a, b in zip(curve, curve[1:])]
    assert all(d > -1e-9 for d in steps)        # monotone
    assert max(steps) <= 0.55                   # anti-cliff (the clearing mass flattens the valley step)
    assert curve[0] == 0.0 and abs(curve[-1] - 1.0) < 1e-9


def test_determined_is_agent_inaccessible_and_exact():
    table, cells, costs, cov, probe = build_tableau(TRAIL)
    H_all = frozenset(range(len(table)))
    assert determined(table, cov, H_all) == 0                       # nothing determined a priori
    n_cov = len([c for c in cells if c[0] in ("direct", "valley")])
    assert determined(table, cov, frozenset({0})) == n_cov          # one world -> all coverage pinned


def test_variable_cost_sharpens_the_gap():
    # The budget is a COST budget: a costlier clearing raises the opportunity cost of the trail's
    # zero-coverage signposts, widening (never inverting) the gap. The cost knob is real.
    cheap = screen(TrailSpec("cheap", R=8, K=2, Ld=2, Lv=9, trailhead=0,
                             waypoints=(1, 2), landmarks=((3, 4), (3, 4)), budget=4))
    dear = screen(TrailSpec("dear", R=8, K=2, Ld=2, Lv=9, trailhead=0,
                            waypoints=(1, 2), landmarks=((3, 4), (3, 4)), budget=4, cost_clearing=2))
    assert dear["gap_norm"] >= cheap["gap_norm"] - 1e-9
