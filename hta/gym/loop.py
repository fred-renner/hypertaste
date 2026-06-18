"""The curriculum -- the offline LOOP-2 driver (this pass: free, model-free, deterministic).

This pass is the *substrate proof*, not the live loop: seed -> mutate -> ship-gate -> collect
verdicts, with no archive, no LLM, no live champion. It demonstrates that the grammar expands to
gradeable worlds and that the mutation machinery exercises the ship-gate across a correct
admit/reject spread. The live curriculum (smith proposes -> gate -> hand to LOOP 1 -> graduate, with
the archive carrying stepping-stones) lands when LOOP 1 is wired and the LLM inventor enters.

Kept distinct from hta/dgmh/loop.py on purpose: this loop's "evaluate" is the model-free,
deterministic ship-gate, where LOOP 1's is live, stochastic play. Reference: `run_curriculum` in
hta/_trail/world_smith.py.
"""

from __future__ import annotations

from typing import List, Mapping

from hta.config import Config
from hta.gym import smith
from hta.gym.ship_gate import ship_gate
from hta.world.seed import seed_spec


def survey(base: Mapping = None, cfg: Config = None, log=print) -> List[dict]:
    """Ship-gate the seed and each one-step mutation of it; return the verdict records and log a
    one-line summary per world. The deterministic offline spread the substrate is proven on."""
    cfg = cfg or Config()
    base = base or seed_spec()
    worlds = [base, *smith.spread(base)]

    out = []
    for spec in worlds:
        v = ship_gate(spec, cfg)
        out.append(v)
        if v.get("valid"):
            log(f"  {v['name']:18s} fl={v['floor']:.1f} orc={v['oracle']:.1f} gap={v['gap']:.1f} "
                f"reach={v['reachable']:.2f} margin={v['battery_margin']:.2f} "
                f"champ={v['champion_norm']:.2f} fix={v['fix_norm']:.2f} "
                f"=> {'SHIP' if v['ship'] else 'HOLD'}")
        else:
            log(f"  {v['name']:18s} INVALID: {v['issue']}  => HOLD")
    return out
