"""Tests for the dumb-player battery (hta/gym/battery.py) -- the world-bracketing screen.

The load-bearing claims:
- On the seed, best-possible play clears the strongest scripted player by the configured margin --
  the stronger hardness bar (over greedy/random/sweep/2-step-lookahead, not just the lazy floor).
- The ZPD bracket is clean: the greedy champion analogue stalls at the floor while the scout-the-
  path fix reaches the oracle band -- *room for taste* in the world's geometry.
- A flattened world (the prerequisite path shortened so a 2-step planner can see the payoff) has
  NO room: the best scripted player ~ the oracle -> the battery margin collapses -> reject cheaply.
"""

from hta.config import Config
from hta.gym import battery, smith
from hta.world import spec as S
from hta.world.seed import seed_spec

CFG = Config()


def test_seed_oracle_clears_the_battery_by_margin():
    rep = battery.battery_report(S.build(seed_spec(), seed=0))
    band = rep["oracle"] - rep["floor"]
    margin = (rep["oracle"] - rep["best_naive_raw"]) / band
    assert margin >= CFG.world_battery_margin
    # and every scripted member really is below the oracle (best-play is not just tying a dumb rule)
    assert rep["best_naive_norm"] < 1.0


def test_seed_zpd_bracket_is_clean():
    rep = battery.battery_report(S.build(seed_spec(), seed=0))
    assert rep["champion_norm"] <= CFG.world_zpd_fail_bar     # greedy stalls (ignores the gates)
    assert rep["fix_norm"] >= CFG.world_zpd_solve_bar         # scout-the-path reaches the band
    assert rep["fix_norm"] > rep["champion_norm"]             # a real gap = room for taste


def test_flat_world_has_no_room():
    # Shorten the prerequisite path until a 2-step planner can see the payoff: greedy/lookahead ~
    # oracle, so the margin collapses and the world is rejected (nothing to learn).
    rep = battery.battery_report(S.build(smith.flatten(seed_spec()), seed=0))
    band = rep["oracle"] - rep["floor"]
    margin = (rep["oracle"] - rep["best_naive_raw"]) / band if band > 1e-9 else 0.0
    assert margin < CFG.world_battery_margin


def test_battery_is_deterministic():
    # The whole battery (including the seeded 'random' member) is reproducible run-to-run.
    a = battery.battery_report(S.build(seed_spec(), seed=0))
    b = battery.battery_report(S.build(seed_spec(), seed=0))
    assert a == b
