"""Tests for the gym's ship-gate (hta/gym/ship_gate.py) and the mutation spread (hta/gym/smith.py).

The load-bearing claims, all model-free and deterministic:
- The seed SHIPS: valid + hard + solvable + zpd-capable structure (the champion analogue stalls, the
  fix succeeds) -- the substrate's certified starting world.
- The mutation machinery exercises the gate across the EXPECTED admit/reject spread:
    * deepen the prerequisite path -> still ships, and harder (a deeper horizon, higher ceiling);
    * remove a gate layer (flatten) -> reject as trivial (a 2-step planner sees the payoff);
    * over-tighten the budget -> reject as unsolvable (no method can reach the payoff in budget).
- The smith proposes STRUCTURE only -- never a score (an integrity invariant).
"""

from hta.config import Config
from hta.gym import smith
from hta.gym.ship_gate import ship_gate
from hta.world.seed import seed_spec

CFG = Config()


def test_seed_ships():
    v = ship_gate(seed_spec(), CFG)
    assert v["ship"] is True
    assert v["valid"] and v["hard"] and v["solvable"] and v["zpd_capable"]
    assert v["champion_norm"] <= CFG.world_zpd_fail_bar       # the champion analogue stalls
    assert v["fix_norm"] >= CFG.world_zpd_solve_bar           # the fix reaches the band


def test_deepen_still_ships_and_is_harder():
    seed = seed_spec()
    base = ship_gate(seed, CFG)
    deeper = ship_gate(smith.deepen(seed), CFG)
    assert deeper["ship"] is True
    assert deeper["oracle"] > base["oracle"]                  # a higher ceiling = harder
    assert deeper["champion_norm"] <= CFG.world_zpd_fail_bar  # still beyond the greedy champion


def test_remove_gate_rejected_as_trivial():
    # Flatten the path so a 2-step planner can see the payoff: not hard -> HOLD.
    v = ship_gate(smith.flatten(seed_spec()), CFG)
    assert v["ship"] is False
    assert v["hard"] is False


def test_over_tighten_rejected_as_unsolvable():
    # Two budget tightenings: the scout cannot complete in budget 2 -> not solvable -> HOLD.
    tight = smith.tighten_budget(smith.tighten_budget(seed_spec()))
    v = ship_gate(tight, CFG)
    assert v["ship"] is False
    assert v["solvable"] is False


def test_invalid_spec_holds_without_grading():
    bad = {**seed_spec(), "bait": []}
    v = ship_gate(bad, CFG)
    assert v["valid"] is False and v["ship"] is False
