"""Tests for the grader (hta/lab/scoring.py), driven by a minimal world-agnostic fixture.

The fixture carries no world-family DNA -- it is the smallest world that exhibits a real
allocation gap (an instrument unlocks scored cells that the lazy floor cannot reach), so it
exercises every engine path: belief partition, the adaptive oracle, the lazy floor, the
coverage cap, the band normalization, and the ungameable-guess guarantee. Endpoints are
hand-computed (floor=1, oracle=3) so the test pins the math, not just its own output.
"""

from dataclasses import dataclass
from itertools import product

from hta.config import Config
from hta.lab import scoring


@dataclass(frozen=True)
class MiniWorld:
    """Two hidden bits (r0, r1) -> 4 hypotheses. Positions, by index:
        0  direct   : scored + probeable, value = r0  (a directly-earnable cell)
        1  key      : probeable, NOT scored, value = r1  (an instrument)
        2,3,4 target: scored, NOT probeable, value = r1  (inference-only; pinned by 'key')
    All costs 1. Budget 1, so one probe: the lazy floor can only take the one direct cell
    (=1); the oracle spends its probe on 'key', which pins all three targets at once (=3).
    """
    budget: int = 1

    def hypotheses(self):
        return list(product(range(2), repeat=2))      # (r0, r1)

    def positions(self):
        return (0, 1, 2, 3, 4)

    def cost(self, p):
        return 1

    def probeable(self, p):
        return p in (0, 1)

    def scored(self, p):
        return p in (0, 2, 3, 4)

    def observe(self, p, h):
        r0, r1 = h
        return r0 if p == 0 else r1                    # direct=r0; key & targets=r1


def test_floor_and_oracle_endpoints():
    w = MiniWorld()
    assert scoring.floor(w) == 1.0
    assert scoring.oracle(w) == 3.0
    assert scoring.oracle(w) > scoring.floor(w)        # a real gap exists


def test_score_run_floor_level_is_zero():
    # Lazy run under truth (r0=1, r1=0): probe the one direct cell, submit it correctly.
    w = MiniWorld()
    run = {"observations": [(0, 1)], "submission": {0: 1}}
    assert scoring.score_run(w, run) == 0.0


def test_score_run_oracle_level_is_one():
    # Sharp run under truth (r0=1, r1=0): probe 'key' (sees r1=0), submit the three targets.
    w = MiniWorld()
    run = {"observations": [(1, 0)], "submission": {2: 0, 3: 0, 4: 0}}
    assert scoring.score_run(w, run) == 1.0


def test_guessing_unprobed_unpinned_cell_earns_nothing():
    # Same sharp run, but also guess the un-probed 'direct' cell. r0 is unknown, so 'direct'
    # is not pinned -> it must not count, even though the guess (0) is submitted.
    w = MiniWorld()
    cheated = {"observations": [(1, 0)], "submission": {2: 0, 3: 0, 4: 0, 0: 0}}
    honest = {"observations": [(1, 0)], "submission": {2: 0, 3: 0, 4: 0}}
    assert scoring.score_run(w, cheated) == scoring.score_run(w, honest) == 1.0


def test_no_submission_scores_floor():
    w = MiniWorld()
    assert scoring.score_run(w, {"observations": [(1, 0)], "submission": {}}) == 0.0


def test_grade_world_hard_and_solvable():
    g = scoring.grade_world(MiniWorld(), Config())
    assert g["floor"] == 1.0 and g["oracle"] == 3.0
    assert g["scorable"] == 4 and g["reachable"] == 0.75
    assert g["hard"] is True and g["solvable"] is True


def test_grade_world_degenerate_is_neither():
    # Budget 0: no probe affordable, so floor == oracle == 0 -> no gap, nothing reachable.
    g = scoring.grade_world(MiniWorld(budget=0), Config())
    assert g["gap"] == 0.0
    assert g["hard"] is False and g["solvable"] is False
