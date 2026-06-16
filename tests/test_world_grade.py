"""Grading-engine tests — the integrity floor's math (hta/world/grade.py). Deterministic, pure
compute, no API cost.

The load-bearing claims:
- The references order correctly: floor <= best heuristic <= oracle <= clairvoyant.
- A FORK world is above threshold: the belief-MDP oracle strictly beats every generic planner (incl.
  2-step lookahead), with an anti-cliff ramp — the optimal allocation is NOT a shallow rule.
- A slack-budget control is below threshold (allocation is trivial when you can probe everything).
- The dumb scorer is ungameable: credit is capped to cells the agent's OWN probes logically pin; a
  guess on an un-probed cell earns zero; no submission earns zero.
- instance0 (the proof-of-principle world) clears the build-screen.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.world import grade  # noqa: E402
from hta.world.instances import instance0  # noqa: E402
from hta.world.language import Chain, Clearing, Fork, WorldSpec, build_tableau  # noqa: E402

FORK = WorldSpec("fork-small", R=8, K=2, budget=4, regions=(
    Fork(gate=0, Lv=9, chains=(Chain(1, ((2, 3),)), Chain(4, ((5, 6),)))), Clearing(7)))
# A below-threshold control: a slack budget large enough to probe every clearing AND walk a trail, so
# greedy allocation reaches the oracle (nothing to be clever about).
SLACK = WorldSpec("slack", R=8, K=2, budget=20, regions=(
    Fork(gate=0, Lv=9, chains=(Chain(1, ((2, 3),)),)), Clearing(4), Clearing(5)))


def test_reference_ordering_holds():
    s = grade.screen(FORK)
    assert s["floor"] <= s["best_heur"] <= s["oracle"] <= s["clairvoyant"] + 1e-9
    assert all(s["oracle"] >= h - 1e-9 for h in s["heurs"].values())


def test_fork_is_above_threshold_and_anti_cliff():
    # The gap needs enough off-trail bait that a zero-coverage signpost read has real opportunity cost,
    # so the canonical instance0 (3 clearings, tight budget) is the above-threshold fixture; the tiny
    # 1-clearing FORK above is only for the cheap structural checks (it is intentionally below the gate).
    s = grade.screen(instance0(), clair=False)
    assert s["oracle"] > s["best_heur"] + 1e-9
    assert s["gap_norm"] >= 0.15
    assert s["heurs"]["lookahead2"] < s["oracle"] - 1e-9         # not even a 2-step planner reaches it
    assert s["ramp_monotone"] and s["ramp_maxstep"] <= 0.55


def test_slack_budget_is_below_threshold():
    s = grade.screen(SLACK, clair=False)
    assert s["gap_norm"] < 0.15                                  # allocation trivial -> no gap


def test_instance0_clears_the_build_screen():
    s = grade.screen(instance0(), clair=False)
    assert s["floor"] == 4 and s["oracle"] == 11                 # the proven decoy band
    assert s["gap_norm"] >= 0.15 and 0.15 <= s["heur_norm"] <= 0.80
    assert s["ramp_monotone"] and s["ramp_maxstep"] <= 0.55


def test_scorer_caps_credit_to_pinned_cells():
    # The judge is ungameable: a coverage cell counts only if the agent's probes logically pin it AND
    # it submitted the correct value. Probe the clearing block (var 7), then submit it -> earns it.
    spec = FORK
    table, cells, costs, cov, probe = build_tableau(spec)
    hyps_idx0 = (0,) * spec.R
    # find the clearing columns (var 7) and their true values under the all-zero world
    clearing_cols = [i for i, c in enumerate(cells) if c[0] == "direct"]
    log = [{"col": c, "value": spec.cell_value(cells[c], hyps_idx0), "cost": 1, "via": "self"}
           for c in clearing_cols]
    submitted = {c: spec.cell_value(cells[c], hyps_idx0) for c in clearing_cols}
    earned = grade.coverage_earned(spec, log, submitted)
    assert earned == len(clearing_cols)                          # all probed+submitted clearings earned


def test_unprobed_guess_and_no_submission_earn_zero():
    spec = FORK
    table, cells, costs, cov, probe = build_tableau(spec)
    valley_cols = [i for i, c in enumerate(cells) if c[0] == "valley"]
    # guess valley cells WITHOUT probing anything -> not pinned -> zero credit even if values are right
    guess = {c: spec.cell_value(cells[c], (0,) * spec.R) for c in valley_cols}
    assert grade.coverage_earned(spec, log=[], submitted=guess) == 0
    assert grade.coverage_earned(spec, log=[], submitted=None) == 0    # no submission -> floor


def test_floor_is_the_no_inference_walker():
    # The floor probes the cheapest coverage-and-probeable cells (the clearings) up to budget. FORK
    # has ONE clearing block (var 7, Ld=2), so only 2 cells are both coverage and probeable -> floor 2
    # even though the budget is 4 (a valley is coverage but NOT probeable; signposts pay no coverage).
    assert grade.floor_value(FORK) == 2
