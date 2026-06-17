"""The world-state machine for ONE episode — the substrate the model-orchestrated harness confines
the player to. It holds the hidden world (a validated `WorldSpec` + the seed variable values), the
global COST budget, an editable within-episode scratchpad, and the probe log; it exposes the
orchestration primitives as plain methods. `server.py` is a thin stdio-MCP wrapper around this
object, so all the load-bearing logic (budget accounting, the airgap of "values only through probe",
the spawn carve-out, the band judge) is pure Python and unit-tested offline — only the wrapper needs
a live `claude -p`.

Two roles share the machine; the wrapper grants a different toolset to each (the airgap):
  * **top**    — the playbook-driven session: probe, remaining, world_map, mem_read, mem_patch,
                 submit_map, spawn.
  * **worker** — a fresh confined session a spawn carved a sub-budget for: probe, remaining only. It
                 sees only its task + budget (no playbook, no scratchpad, no top context).

The judge (`score`) is the integrity floor, lifted to coverage: a dumb deterministic function of the
probe LOG and the submitted map (`hta.world.grade`), never an LLM. The hidden values live ONLY in
this object (and the probe server's process); the player reaches them solely through `probe`.
"""

import json
from typing import Dict, List, Optional, Tuple

from ...world import grade
from ...world.instances import draw_hstar
from ...world.language import WorldSpec, build_tableau

__all__ = ["EpisodeState", "canonical_spec", "draw_hstar", "normalize",
           "state_to_env", "state_from_env", "spec_to_dict", "spec_from_dict"]

# Re-exports so the loop/server depend on the episode surface, not deep world internals.
from ...world.grade import normalize  # noqa: E402
from ...world.instances import canonical_spec  # noqa: E402


def spec_to_dict(spec: WorldSpec) -> dict:
    return spec.to_dict()


def spec_from_dict(d: dict) -> WorldSpec:
    """Rebuild the spec from a declarative parts-list. Data-driven (safe-eval, lifted): a validated
    structural spec, never code."""
    return WorldSpec.from_dict(d)


class EpisodeState:
    """One episode's mutable world state. Construct with the public spec + the hidden seed; the seed
    lives only here (the player reaches it solely through `probe`)."""

    def __init__(self, spec: WorldSpec, hstar: Tuple[int, ...], budget: Optional[int] = None):
        self.spec = spec
        self.hstar = tuple(hstar)
        self.budget = spec.budget if budget is None else int(budget)
        self.used = 0                       # cost spent (top probes + committed worker carve-outs)
        self.log: List[dict] = []           # every observation: {col, value, cost, via}
        self.spawns: List[dict] = []        # spawn records (conduct, for the report)
        self.mem = ""                       # the within-episode scratchpad (resets per episode)
        self.submitted: Optional[Dict[int, int]] = None
        self.done = False
        self.table, self.cells, self.costs, self.cov_cols, self.probe_cols = build_tableau(spec)
        self._probe_set = set(self.probe_cols)

    # ---- helpers ----
    def remaining_cost(self) -> int:
        return max(0, self.budget - self.used)

    def _true_value(self, col: int) -> int:
        return self.spec.cell_value(self.cells[col], self.hstar)

    # ---- the orchestration primitives (each returns a JSON-able dict) ----
    def probe(self, index) -> dict:
        """Reveal one cell's hidden value, charging its cost against the global budget. Only
        signpost/clearing cells are probeable; a valley is inference-only (reconstructed, never
        drilled). A malformed or unaffordable probe is reported, not charged."""
        if not isinstance(index, int) or isinstance(index, bool) or index not in self._probe_set:
            return {"value": None, "remaining": self.remaining_cost(),
                    "error": "not a probeable cell index"}
        cost = self.costs[index]
        if cost > self.remaining_cost():
            return {"value": None, "remaining": self.remaining_cost(),
                    "error": "insufficient budget for this probe's cost", "cost": cost}
        self.used += cost
        val = self._true_value(index)
        self.log.append({"col": index, "value": val, "cost": cost, "via": "self"})
        return {"value": val, "remaining": self.remaining_cost(), "cost": cost}

    def remaining(self) -> dict:
        return {"remaining": self.remaining_cost()}

    def world_map(self) -> dict:
        """The PUBLIC rules of the game (the regions' wiring, the cell layout with costs/roles, the
        value law) — the variable VALUES absent. Delegated to `spec.world_map_public`, so any world
        the language grows describes itself through this unchanged airgap method. `submit_map` keys
        and `probe` indices are the `col` fields here."""
        return self.spec.world_map_public(self.remaining_cost())

    def mem_read(self) -> dict:
        return {"text": self.mem}

    def mem_patch(self, find=None, replace="") -> dict:
        """Incremental scratchpad edit (NOT full-replace, NOT append-only — so compression,
        forgetting and buffering are all reachable). `find` empty/None => append `replace`; `find`
        present => replace its first occurrence with `replace` (empty `replace` deletes). The note
        SCHEMA is deliberately withheld — it is for the loop to invent, not the substrate to impose."""
        replace = "" if replace is None else str(replace)
        if not find:
            self.mem = (self.mem + ("\n" if self.mem and not self.mem.endswith("\n") else "") + replace)
            return {"ok": True, "len": len(self.mem)}
        find = str(find)
        if find not in self.mem:
            return {"ok": False, "reason": "find-text not present", "len": len(self.mem)}
        self.mem = self.mem.replace(find, replace, 1)
        return {"ok": True, "len": len(self.mem)}

    def submit_map(self, values) -> dict:
        """End the episode with a reconstruction: {col: value} over the cells you claim to know
        (coverage cells matter for the score). Accepted == well-formed; correctness is judged
        afterward by `score`, never revealed here."""
        parsed = self._parse_submission(values)
        self.submitted = parsed
        self.done = True
        return {"accepted": parsed is not None, "n_cells": (len(parsed) if parsed else 0)}

    def _parse_submission(self, values) -> Optional[Dict[int, int]]:
        out: Dict[int, int] = {}
        if isinstance(values, dict):
            items = values.items()
        elif isinstance(values, list):
            items = zip(self.cov_cols, values)      # a flat list -> col->value over coverage cols
        else:
            return None
        for k, v in items:
            try:
                col = int(k)
                val = int(v)
            except (TypeError, ValueError):
                return None
            if isinstance(v, bool) or not (0 <= col < len(self.cells)):
                return None
            out[col] = val
        return out

    # ---- spawn carve-out accounting (the worker subprocess is run by the wrapper) ----
    def grant_spawn(self, budget) -> int:
        """Carve a sub-budget for ONE worker: min(requested, remaining). The worker runs against its
        OWN isolated copy of this world; only what it spends is committed (unused returns). Spawns are
        sequential, so no live budget is reserved here."""
        try:
            b = int(budget)
        except (TypeError, ValueError):
            return 0
        return max(0, min(b, self.remaining_cost()))

    def commit_spawn(self, task: str, observations, used: int, report: str = "") -> dict:
        """Fold a finished worker back in: charge only what it `used` and merge its observations into
        the log so they count toward coverage (the top must still submit those cells to earn them)."""
        obs = []
        for item in (observations or []):
            try:
                col, val = int(item[0]), int(item[1])
            except (TypeError, ValueError, IndexError):
                continue
            obs.append([col, val])
            self.log.append({"col": col, "value": val, "cost": 0, "via": "worker"})
        used = max(0, min(int(used or 0), self.remaining_cost()))
        self.used += used
        rec = {"task": task, "used": used, "n_obs": len(obs), "report": report}
        self.spawns.append(rec)
        return {"observations": obs, "report": report, "used": used,
                "remaining": self.remaining_cost()}

    # ---- result persistence (the dropbox the parent process reads after the session) ----
    def result(self) -> dict:
        return {"log": self.log, "spawns": self.spawns, "mem": self.mem,
                "submitted": (self.submitted or {}), "used": self.used, "done": self.done,
                "observations": [[e["col"], e["value"]] for e in self.log]}

    # ---- the judge (integrity floor, lifted to coverage; delegated to the dumb scorer) ----
    def score(self) -> dict:
        return grade.score_submission(self.spec, self.log, self.submitted, used=self.used)


# ---------------------------------------------------------------------------
# Env (de)serialization — how the hidden world rides to a probe-server subprocess. The seed lives
# ONLY in the server's env, never on the player's channel.
# ---------------------------------------------------------------------------
def state_to_env(spec: WorldSpec, hstar: Tuple[int, ...], budget: int) -> dict:
    return {"HTA_WORLD": json.dumps(spec_to_dict(spec)),
            "HTA_HSTAR": json.dumps(list(hstar)), "HTA_BUDGET": str(int(budget))}


def state_from_env(env: dict) -> EpisodeState:
    spec = spec_from_dict(json.loads(env["HTA_WORLD"]))
    hstar = tuple(json.loads(env["HTA_HSTAR"]))
    budget = int(env.get("HTA_BUDGET", spec.budget))
    state = EpisodeState(spec, hstar, budget=budget)
    if env.get("HTA_SITUATION"):                # a constructed mid-episode state (replayed prefix)
        d = json.loads(env["HTA_SITUATION"])
        for col in d.get("probed", []):
            state.probe(int(col))
        if d.get("mem"):
            state.mem = str(d["mem"])
    return state
