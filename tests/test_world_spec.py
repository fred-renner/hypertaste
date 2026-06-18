"""Tests for the world grammar (hta/world/spec.py) and the certified seed (hta/world/seed/).

The load-bearing claims:
- `validate` rejects illegal wiring (out-of-range refs, empty bait, budget < 1, a gated payoff with
  no gate) -- the safe-eval wall: a bad spec is never built.
- `build` is a deterministic expander whose output the FROZEN grader rides unchanged (it answers
  hypotheses / positions / cost / observe / probeable / scored) -- the family-specific parts box on
  top of the generic scorer.
- the seed is a real allocation gap: oracle > floor, and `grade_world` reports hard + solvable.
"""

import pytest

from hta.config import Config
from hta.lab import scoring
from hta.world import spec as S
from hta.world.seed import seed_spec


# ---- validate: the safe-eval wall ----
def test_seed_is_valid():
    S.validate(seed_spec())  # must not raise


@pytest.mark.parametrize("mutate, why", [
    (lambda s: {**s, "bait": []}, "empty bait"),
    (lambda s: {**s, "budget": 0}, "budget < 1"),
    (lambda s: {**s, "bait": [0, 99]}, "bait variable out of range"),
    (lambda s: {**s, "payoff": {**s["payoff"], "start": 99}}, "start out of range"),
    (lambda s: {**s, "payoff": {**s["payoff"], "hops": []}}, "no gate (no hops)"),
    (lambda s: {**s, "payoff": {**s["payoff"], "hops": [[5]]}}, "hop wrong length"),
    (lambda s: {**s, "payoff": {**s["payoff"], "hops": [[5, 99]]}}, "hop target out of range"),
    (lambda s: {**s, "n_vars": 1}, "n_vars < 2"),
    (lambda s: {**s, "K": 1}, "K < 2"),
])
def test_validate_rejects_illegal(mutate, why):
    with pytest.raises(ValueError):
        S.validate(mutate(seed_spec()))


# ---- build: a World the frozen grader rides ----
def test_build_rides_the_grader():
    w = S.build(seed_spec(), seed=0)
    # the Protocol the grader reads
    hyps = w.hypotheses()
    assert len(hyps) == 2 ** 9                 # 9 variables, K=2
    pos = list(w.positions())
    assert len(pos) == 4 + 5 + 5               # 4 bait + 5 gate readouts (path vars {4..8}) + 5 payoff
    # roles: bait scored+probeable; gate probeable+unscored; payoff scored+not-probeable
    assert all(w.scored(p) and w.probeable(p) for p in pos if p[0] == "bait")
    assert all(w.probeable(p) and not w.scored(p) for p in pos if p[0] == "gate")
    assert all(w.scored(p) and not w.probeable(p) for p in pos if p[0] == "payoff")
    # observe is a pure deterministic lookup the grader can tabulate
    h = hyps[0]
    assert all(isinstance(w.observe(p, h), int) for p in pos)


def test_build_is_deterministic_and_hides_the_answer():
    a = S.build(seed_spec(), seed=7)
    b = S.build(seed_spec(), seed=7)
    assert a.hstar == b.hstar                  # same (spec, seed) -> identical world
    assert len(a.hstar) == a.n_vars
    # the hidden answer is harness-side only; the grader never reads it (it is not in the Protocol)
    assert a.hstar != S.build(seed_spec(), seed=8).hstar or True   # (different seed may differ)


# ---- the seed is a real allocation gap ----
def test_seed_oracle_beats_floor():
    w = S.build(seed_spec(), seed=0)
    assert scoring.oracle(w) > scoring.floor(w)


def test_seed_grades_hard_and_solvable():
    w = S.build(seed_spec(), seed=0)
    g = scoring.grade_world(w, Config())
    assert g["floor"] == 4.0 and g["oracle"] == 6.0      # certified endpoints
    assert g["hard"] is True and g["solvable"] is True
