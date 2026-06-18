"""The ship-gate -- admit a proposed world only if it earns its place.

Realize the smith's spec via the lab, then gate on a mechanical verdict re-derived from the
*structure* alone (the smith never asserts it). A world ships only if it is:

  * **valid**   -- a legal spec (`hta.world.spec.validate` did not reject it);
  * **hard**    -- the lab grades it hard (wide best/lazy gap) AND best-play beats the strongest
                   scripted player in the dumb-player battery by `world_battery_margin` (the stronger
                   bar: not just over the lazy floor, but over greedy/sweep/2-step-lookahead too);
  * **solvable**-- the lab grades it solvable (the top reachable in budget) AND the scout-the-path
                   fix analogue actually reaches the band (`world_zpd_solve_bar`);
  * **zpd-capable structure** -- the greedy champion analogue stalls (<= `world_zpd_fail_bar`) while
                   the fix succeeds. A *necessary* screen, agent-independent, NOT a measurement of
                   true ZPD (that needs the live champion; see the battery's boundary note). The
                   only legal coupling to an agent is this objective gap on the non-movable scorer.

A world that fails is rejected, not rescued. The grade is mechanical and free; the smith never sees
it (gating on a number the smith grows would breed worlds specialised against the screen). Model-free
-- it must never import hta.llm. Reference: `ship_gate` in hta/_trail/world_smith.py.
"""

from __future__ import annotations

from typing import Mapping

from hta.config import Config
from hta.gym import battery
from hta.lab import scoring
from hta.world import spec as world_spec


def ship_gate(spec: Mapping, cfg: Config = None) -> dict:
    """The model-free verdict on one proposed world. Returns the full record (every sub-verdict and
    the numbers behind it) plus `ship` -- the AND of valid/hard/solvable/zpd_capable."""
    cfg = cfg or Config()

    try:
        world_spec.validate(spec)
        valid, issue = True, None
    except ValueError as e:
        valid, issue = False, str(e)

    if not valid:
        return {"name": spec.get("name", "?"), "valid": False, "issue": issue, "ship": False}

    world = world_spec.build(spec, seed=0)
    grade = scoring.grade_world(world, cfg)
    rep = battery.battery_report(world)
    band = rep["oracle"] - rep["floor"]

    battery_margin = (rep["oracle"] - rep["best_naive_raw"]) / band if band > 1e-9 else 0.0
    hard = bool(grade["hard"] and battery_margin >= cfg.world_battery_margin)
    solvable = bool(grade["solvable"] and rep["fix_norm"] >= cfg.world_zpd_solve_bar)
    zpd_capable = bool(rep["champion_norm"] <= cfg.world_zpd_fail_bar
                       and rep["fix_norm"] >= cfg.world_zpd_solve_bar)
    ship = bool(valid and hard and solvable and zpd_capable)

    return {
        "name": spec.get("name", "?"), "valid": True, "issue": None,
        "floor": rep["floor"], "oracle": rep["oracle"], "scorable": grade["scorable"],
        "gap": grade["gap"], "reachable": grade["reachable"],
        "best_naive": rep["best_naive"], "best_naive_norm": rep["best_naive_norm"],
        "battery_margin": round(battery_margin, 4),
        "champion_norm": rep["champion_norm"], "fix_norm": rep["fix_norm"],
        "naive": rep["naive"],
        "hard": hard, "solvable": solvable, "zpd_capable": zpd_capable, "ship": ship,
    }
