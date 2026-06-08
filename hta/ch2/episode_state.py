"""The frozen world-state machine for ONE Chapter-2 episode — the substrate the
model-orchestrated harness (option B, RESET_DESIGN.md -> "The harness spec") confines the player
to. It holds the hidden world (a realized `TrailSpec` + the seed register values), the global
**cost** budget, an editable within-episode scratchpad, and the probe log; it exposes the seven
orchestration primitives as plain methods. `probe_server.py` is a thin stdio-MCP wrapper around
this object, so all the load-bearing logic (budget accounting, the airgap of "values only through
probe", the spawn carve-out, the band judge) is pure Python and unit-tested offline — the only
thing that needs a live `claude -p` is the wrapper.

Two roles share the machine; the wrapper grants a different toolset to each (the airgap):
  * **top**     — the playbook-driven Haiku session. Tools: probe, remaining, world_map, mem_read,
                  mem_patch, submit_map, spawn.
  * **worker**  — a fresh confined session a spawn carved a sub-budget for. Tools: probe, remaining.
                  It sees only its task + budget (no playbook, no scratchpad, no top context).

The judge (`score`) is the integrity floor, lifted to coverage: it is a dumb deterministic
function of the probe LOG and the submitted map — never an LLM, never the player's word for it.
Coverage credit is **capped to cells the agent's own probes logically pin** (so guessing un-probed
cells under a small K cannot farm the band), then normalized into the model-free floor->oracle band
(`hta/ch2/anchor.py`). Allocation is the whole game: which probes you spend decide which cells your
evidence pins, and that is what the band measures.
"""

import json
from typing import Dict, List, Optional, Tuple

from . import anchor


# ---------------------------------------------------------------------------
# The canonical anchor world (the build-screened run-pick, run_anchor.py). The PUBLIC structure
# (the pointer tree, the cell layout, the costs, the budget) is constant across episodes; only the
# hidden seed (the register values -> where the realized trail ends) is drawn fresh per episode.
# ---------------------------------------------------------------------------
ANCHOR = dict(name="anchor", R=10, K=2, Ld=2, Lv=9, trailhead=0,
              waypoints=(1, 2), landmarks=((3, 4), (5, 6)), budget=3)


def canonical_spec() -> anchor.TrailSpec:
    return anchor.TrailSpec(**ANCHOR)


def spec_to_dict(spec: anchor.TrailSpec) -> dict:
    """Serialize a TrailSpec to a JSON-able dict (tuples -> lists) so it can ride to the probe
    server in a server-only env var — the hidden seed never touches the player's channel."""
    return {"name": spec.name, "R": spec.R, "K": spec.K, "Ld": spec.Ld, "Lv": spec.Lv,
            "trailhead": spec.trailhead, "waypoints": list(spec.waypoints),
            "landmarks": [list(row) for row in spec.landmarks], "budget": spec.budget,
            "Ls": spec.Ls, "cost_signpost": spec.cost_signpost, "cost_clearing": spec.cost_clearing}


def spec_from_dict(d: dict) -> anchor.TrailSpec:
    return anchor.TrailSpec(
        name=d["name"], R=d["R"], K=d["K"], Ld=d["Ld"], Lv=d["Lv"], trailhead=d["trailhead"],
        waypoints=tuple(d["waypoints"]), landmarks=tuple(tuple(r) for r in d["landmarks"]),
        budget=d["budget"], Ls=d.get("Ls", 1), cost_signpost=d.get("cost_signpost", 1),
        cost_clearing=d.get("cost_clearing", 1))


def draw_hstar(spec: anchor.TrailSpec, seed: int) -> Tuple[int, ...]:
    """A fresh hidden world: a uniform register assignment (the only hidden information). Different
    seeds end the trail on different landmark registers, so the winning policy's CONTENT is
    learnable only by playing this instance, never read off the public structure."""
    import random
    rng = random.Random(seed)
    return tuple(rng.randrange(spec.K) for _ in range(spec.R))


# ---------------------------------------------------------------------------
# The episode state.
# ---------------------------------------------------------------------------
class EpisodeState:
    """One episode's mutable world state. Construct with the public spec + the hidden seed; the
    seed lives only here (the player reaches it solely through `probe`)."""

    def __init__(self, spec: anchor.TrailSpec, hstar: Tuple[int, ...], budget: Optional[int] = None):
        self.spec = spec
        self.hstar = tuple(hstar)
        self.budget = spec.budget if budget is None else int(budget)
        self.used = 0                       # cost spent (top probes + committed worker carve-outs)
        self.log: List[dict] = []           # every observation: {col, value, cost, via}
        self.spawns: List[dict] = []        # spawn records (conduct, for the report)
        self.mem = ""                       # the within-episode scratchpad (resets per episode)
        self.submitted: Optional[Dict[int, int]] = None
        self.done = False
        # The full tableau is what makes the judge a dumb deterministic f(structure, observations):
        # 1024 rows on the anchor, built once.
        self.table, self.cells, self.costs, self.cov_cols, self.probe_cols = anchor.build_tableau(spec)
        self._probe_set = set(self.probe_cols)

    # ---- helpers ----
    def remaining_cost(self) -> int:
        return max(0, self.budget - self.used)

    def _true_value(self, col: int) -> int:
        return anchor.cell_value(self.spec, self.cells[col], self.hstar)

    # ---- the seven primitives (each returns a JSON-able dict) ----
    def probe(self, index) -> dict:
        """Reveal one cell's hidden value, charging its cost against the global budget. Only
        signpost/clearing cells are probeable; the valley is inference-only (reconstructed, never
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
        """The PUBLIC rules of the game: the pointer tree (trailhead -> waypoint -> landmark), the
        cell layout with costs and roles, and the deterministic VALUE LAW (`value_rule`). The
        register VALUES are absent — that is the hidden seed. Exposing the law (not the values) is
        what makes reconstruction a reachable LOOKUP for the player: it is public structure (the same
        law the model-free heuristics and oracle are computed under), so it lifts the live agent onto
        the screen's footing without touching the band — what stays hidden, and the whole game, is
        the ALLOCATION (which scarce probes to spend). `submit_map` keys and `probe` indices are the
        `col` fields here."""
        cells = []
        for i, c in enumerate(self.cells):
            entry = {"col": i, "kind": c[0], "cost": self.costs[i],
                     "probeable": i in self._probe_set, "coverage": i in self.cov_cols}
            if c[0] in ("sig", "direct"):
                entry["reg"], entry["pos"] = c[1], c[2]
            else:
                entry["pos"], entry["mirrors"] = c[1], "landmark"  # valley mirrors the landmark register
            cells.append(entry)
        value_rule = (
            "Cell values are a deterministic lookup, never a pattern to guess: a cell's value = "
            "(its register's hidden value + pos) mod K. A signpost or clearing cell uses its own "
            "`reg`; a valley cell (mirrors='landmark') uses the LANDMARK register — the one the "
            "public trail (trailhead -> waypoints[branch] -> landmarks[branch][waypoint]) resolves to "
            "under the hidden values. So once your probes pin a register's value, every cell keyed to "
            "that register is fully determined — you reconstruct it, you do not guess it.")
        return {"R": self.spec.R, "K": self.spec.K, "budget": self.spec.budget,
                "remaining": self.remaining_cost(), "value_rule": value_rule,
                "trail": {"trailhead": self.spec.trailhead, "waypoints": list(self.spec.waypoints),
                          "landmarks": [list(r) for r in self.spec.landmarks]},
                "cells": cells}

    def mem_read(self) -> dict:
        return {"text": self.mem}

    def mem_patch(self, find=None, replace="") -> dict:
        """Incremental scratchpad edit (NOT full-replace, NOT append-only — so compression,
        forgetting and buffering are all reachable). `find` empty/None => append `replace`; `find`
        present => replace its first occurrence with `replace` (empty `replace` deletes). The note
        SCHEMA (slots, buffers, what to retain) is deliberately withheld — it is for the loop to
        invent and write into the playbook, not for the substrate to impose."""
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
        (coverage cells matter for the score). Accepted == well-formed (a dict/list of ints over
        valid columns); correctness is judged afterward by `score`, never revealed here."""
        parsed = self._parse_submission(values)
        self.submitted = parsed
        self.done = True
        return {"accepted": parsed is not None,
                "n_cells": (len(parsed) if parsed else 0)}

    def _parse_submission(self, values) -> Optional[Dict[int, int]]:
        out: Dict[int, int] = {}
        if isinstance(values, dict):
            items = values.items()
        elif isinstance(values, list):
            # a flat list is read as col->value over the coverage columns, in order
            items = zip(self.cov_cols, values)
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
        OWN isolated copy of this world with this budget; only what it actually spends is committed
        (unused returns). Spawns are sequential, so no live budget is reserved here."""
        try:
            b = int(budget)
        except (TypeError, ValueError):
            return 0
        return max(0, min(b, self.remaining_cost()))

    def commit_spawn(self, task: str, observations, used: int, report: str = "") -> dict:
        """Fold a finished worker back in: charge only what it `used` (carve-out unused returns) and
        merge its observations into the log so they count toward coverage (the top must still submit
        those cells to earn them). Returns the spawn result handed back to the top."""
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

    # ---- the judge (integrity floor, lifted to coverage) ----
    def observed_belief(self) -> frozenset:
        """The hypothesis set consistent with every observation in the log — the agent's realized
        belief. Coverage is measured here, the same `determined` the oracle/floor use."""
        H = frozenset(range(len(self.table)))
        for e in self.log:
            col, val = e["col"], e["value"]
            H = frozenset(h for h in H if self.table[h][col] == val)
        return H

    def coverage_raw(self) -> int:
        """Cells the agent EARNED: coverage cells its probes logically pin AND it submitted
        correctly. Capping to pinned cells makes the judge ungameable (a lucky guess on an
        un-probed cell scores zero); for a pinned cell the value is forced, so a competent agent
        gets it for free. With no submission, nothing is earned (a legitimate worst score)."""
        if not self.submitted:
            return 0
        H = self.observed_belief()
        if not H:
            return 0
        rep = next(iter(H))
        n = 0
        for c in self.cov_cols:
            v = self.table[rep][c]
            if all(self.table[h][c] == v for h in H) and self.submitted.get(c) == v:
                n += 1
        return n

    def score(self) -> dict:
        """Band-normalized coverage: raw earned cells mapped into the model-free floor->oracle band
        (spec-constant references by simulation, `hta/ch2/anchor.py`). norm in [0,1]: 0 == the
        no-inference floor, 1 == the optimal adaptive oracle."""
        raw = self.coverage_raw()
        floor = anchor.floor_value(self.spec)
        oracle = anchor.oracle_value(self.spec)
        norm = normalize(raw, floor, oracle)
        return {"raw": raw, "floor": round(floor, 4), "oracle": round(oracle, 4),
                "norm": round(norm, 4), "determined": int(anchor.determined(
                    self.table, self.cov_cols, self.observed_belief())),
                "used": self.used, "budget": self.budget}


def normalize(raw: float, floor: float, oracle: float) -> float:
    """Map a raw coverage count into the floor->oracle band, clipped to [0, 1]."""
    band = oracle - floor
    if band <= 1e-9:
        return 0.0
    return max(0.0, min(1.0, (raw - floor) / band))


# ---------------------------------------------------------------------------
# Env (de)serialization — how the hidden world rides to a probe-server subprocess. The seed lives
# ONLY in the server's env, never on the player's channel.
# ---------------------------------------------------------------------------
def state_to_env(spec: anchor.TrailSpec, hstar: Tuple[int, ...], budget: int) -> dict:
    return {"HTA_WORLD": json.dumps(spec_to_dict(spec)),
            "HTA_HSTAR": json.dumps(list(hstar)), "HTA_BUDGET": str(int(budget))}


def state_from_env(env: dict) -> EpisodeState:
    spec = spec_from_dict(json.loads(env["HTA_WORLD"]))
    hstar = tuple(json.loads(env["HTA_HSTAR"]))
    budget = int(env.get("HTA_BUDGET", spec.budget))
    return EpisodeState(spec, hstar, budget=budget)
