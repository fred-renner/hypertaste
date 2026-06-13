"""One machine-world episode's mutable state — the substrate the model-orchestrated player is
confined to (the analogue of `episode_state.py` for kit v1). It holds the hidden machine, the probe
budget, an editable scratchpad, the probe log, and the submitted per-output models; it exposes the
body as plain methods, which `machine_server.py` wraps as a stdio-MCP tool channel (the airgap).

The body (the player's hands) is deliberately small for instance 0: `probe`, `remaining`,
`machine_map`, `mem_read`, `mem_patch`, `submit`. No spawn/hierarchy yet — that is a body affordance
to add only if a trajectory shows working-memory pressure (PLAN.md: ratified ring, applied by the
PI). The scoring is the dumb deterministic exam in `machine.py`; it never lives here.
"""

import json
from typing import Dict, List, Optional

from .machine import Blueprint, Machine, draw_machine, score_models


class MachineEpisode:
    """One episode against one realized machine. The machine (with its hidden tables) lives only
    here; the player reaches a value solely through `probe`."""

    def __init__(self, machine: Machine, budget: Optional[int] = None):
        self.machine = machine
        self.budget = machine.budget if budget is None else int(budget)
        self.used = 0
        self.log: List[dict] = []                  # every probe: {output, input, value}
        self.mem = ""                              # within-episode scratchpad (resets per episode)
        self.submitted: Optional[Dict[int, dict]] = None
        self.done = False

    # ---- helpers ----
    def remaining_budget(self) -> int:
        return max(0, self.budget - self.used)

    def _valid(self, output: int, x: int) -> bool:
        return (isinstance(output, int) and not isinstance(output, bool)
                and 0 <= output < len(self.machine.outputs)
                and isinstance(x, int) and not isinstance(x, bool)
                and 0 <= x < self.machine.outputs[output].domain)

    # ---- the body (each returns a JSON-able dict) ----
    def probe(self, output, input) -> dict:
        """Set one output's scalar input and read its value, charging one unit of budget. Probing
        earns nothing toward the score (PLAN.md §2) — it only buys understanding. A malformed or
        unaffordable probe is reported, not charged."""
        if not self._valid(output, input):
            return {"value": None, "remaining": self.remaining_budget(),
                    "error": "output/input out of range (see machine_map)"}
        if self.remaining_budget() <= 0:
            return {"value": None, "remaining": 0, "error": "out of budget"}
        self.used += 1
        val = self.machine.outputs[output].f(input)
        self.log.append({"output": output, "input": input, "value": val})
        return {"value": val, "remaining": self.remaining_budget()}

    def remaining(self) -> dict:
        return {"remaining": self.remaining_budget()}

    def machine_map(self) -> dict:
        return self.machine.public_map(self.remaining_budget())

    def mem_read(self) -> dict:
        return {"text": self.mem}

    def mem_patch(self, find=None, replace="") -> dict:
        """Incremental scratchpad edit (append if `find` empty; else replace first occurrence — empty
        `replace` deletes). The note schema is the player's to invent, never imposed."""
        replace = "" if replace is None else str(replace)
        if not find:
            self.mem = self.mem + ("\n" if self.mem and not self.mem.endswith("\n") else "") + replace
            return {"ok": True, "len": len(self.mem)}
        find = str(find)
        if find not in self.mem:
            return {"ok": False, "reason": "find-text not present", "len": len(self.mem)}
        self.mem = self.mem.replace(find, replace, 1)
        return {"ok": True, "len": len(self.mem)}

    def submit(self, models) -> dict:
        """End the episode with one model per output (the held-out exam grades these). Accepted ==
        well-formed (a dict of output index -> law dict); correctness is judged afterward, never
        revealed here. Omitted outputs are graded as abstain."""
        parsed = self._parse(models)
        self.submitted = parsed
        self.done = True
        return {"accepted": parsed is not None, "n_models": len(parsed) if parsed else 0}

    def _parse(self, models) -> Optional[Dict[int, dict]]:
        if not isinstance(models, dict):
            return None
        out: Dict[int, dict] = {}
        for k, v in models.items():
            try:
                idx = int(k)
            except (TypeError, ValueError):
                return None
            if isinstance(v, dict):
                out[idx] = v
        return out

    # ---- persistence + scoring ----
    def result(self) -> dict:
        return {"log": self.log, "mem": self.mem, "used": self.used,
                "submitted": (self.submitted or {}), "done": self.done}

    def score(self) -> dict:
        return score_models(self.machine, self.submitted)


# ---------------------------------------------------------------------------
# Env (de)serialization — how the hidden machine rides to a probe-server subprocess. The machine
# (with its tables) lives ONLY in the server's env, never on the player's channel.
# ---------------------------------------------------------------------------
def machine_to_env(machine: Machine, budget: Optional[int] = None) -> dict:
    return {"HTA_MACHINE": json.dumps(machine.to_dict()),
            "HTA_MBUDGET": str(int(machine.budget if budget is None else budget))}


def machine_from_env(env: dict) -> MachineEpisode:
    machine = Machine.from_dict(json.loads(env["HTA_MACHINE"]))
    budget = int(env.get("HTA_MBUDGET", machine.budget))
    return MachineEpisode(machine, budget=budget)


# Re-exported so the loop can draw worlds without importing machine.py separately.
__all__ = ["MachineEpisode", "machine_to_env", "machine_from_env",
           "Blueprint", "Machine", "draw_machine"]
