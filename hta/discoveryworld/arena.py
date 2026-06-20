"""The headless DiscoveryWorld adapter -- one scenario variation, driven as text.

This is the harness side of one episode. It wraps Ai2's `DiscoveryWorldAPI` and exposes exactly
the four things the play needs:
  - `catalogue()` -- the public rules: the legal action types + their JSON format + the named
                     teleport locations. Read once by the player (the "world_map" analogue).
  - `observe()`   -- the current *text* observation (location, what's reachable, inventory, nearby
                     objects, the task, the last action's result, steps used/left). The rendered
                     image ("vision") is dropped -- this is a text agent.
  - `act(json)`   -- apply one action and tick the world; return the resulting observation. Each
                     ticking action spends one step; the *step budget* is the scarce resource
                     (Gotchas: "probes, not turns, bind" -- here a world-step is the probe).
  - `scorecard()` -- HARNESS SIDE ONLY. DiscoveryWorld's own deterministic scorecard (the process
                     score + per-criterion breakdown + completion). It carries oracle knowledge and
                     is never placed on the player's tool surface (see server.py / the airgap).

`discoveryworld` is a heavy, OPTIONAL dependency (pygame, numpy, ...). It is imported lazily, so the
stdlib-only test suite and the trail world are unaffected by its absence. The simulator prints a
wall of sprite/asset-loading noise to stdout on construction; we capture it (it must never reach the
MCP server's JSON-RPC stdout) -- see `_quiet`.

Per the integrity floor this module is the world body: it legitimately holds the scorecard (it must,
to score), but the player reaches it only through the confined tools in server.py.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
from typing import Any, Dict, List, Optional

# DiscoveryWorld needs SDL, but we run headless with the dummy video/audio drivers. Set before the
# (lazy) pygame import so a real display is never required.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Terrain that floods `nearbyObjects` (every grass/path/soil tile within 3) but is never an action
# target -- dropped from the observation so the player's context stays about the task, not the lawn.
_TERRAIN = {"grass", "path", "soil", "sand", "wall", "floor", "water"}


@contextlib.contextmanager
def _quiet():
    """Swallow the simulator's stdout chatter (sprite/asset loading, scenario warnings). Must wrap
    every sim call made from inside the MCP server, whose stdout is the JSON-RPC channel."""
    with contextlib.redirect_stdout(io.StringIO()):
        yield


class DiscoveryWorldUnavailable(RuntimeError):
    """Raised when the optional `discoveryworld` package is not installed."""


def _load_api():
    try:
        from discoveryworld.DiscoveryWorldAPI import DiscoveryWorldAPI  # noqa: WPS433
    except Exception as e:  # noqa: BLE001 - surface a clear install hint
        raise DiscoveryWorldUnavailable(
            "the 'discoveryworld' package is required for the arena; "
            "install it with `pip install discoveryworld` (see requirements-bench.txt)") from e
    return DiscoveryWorldAPI


def valid_scenarios() -> Dict[str, Any]:
    """The scenario -> {difficulty, variations} map DiscoveryWorld ships (for the driver/validation)."""
    from discoveryworld.ScenarioMaker import SCENARIO_INFOS  # noqa: WPS433
    return dict(SCENARIO_INFOS)


class Arena:
    """One DiscoveryWorld scenario variation, driven headless as text.

    A *variation* is selected by `seed` (DiscoveryWorld's parametric variation: a different layout /
    data / solution each seed) -- this is the built-in held-out split. `budget` caps the number of
    ticking actions; once spent, `act` refuses and tells the player to stop.
    """

    def __init__(self, scenario: str, difficulty: str, *, seed: int, budget: int,
                 thread_id: int = 1) -> None:
        self.scenario = scenario
        self.difficulty = difficulty
        self.seed = int(seed)
        self.budget = int(budget)
        self._log: List[Dict[str, Any]] = []   # the player's conduct, for the audit/report
        DiscoveryWorldAPI = _load_api()
        with _quiet():
            self.api = DiscoveryWorldAPI(threadID=thread_id)
            ok = self.api.loadScenario(scenario, difficulty, randomSeed=self.seed, numUserAgents=1)
            if not ok:
                raise ValueError(
                    f"DiscoveryWorld rejected scenario={scenario!r} difficulty={difficulty!r}; "
                    f"valid: {valid_scenarios().get(scenario)}")
            # One observation primes taskProgress / step counter.
            self._last = self.api.getAgentObservation(0)

    # ---- public rules (the player may read these freely) -------------------------------------
    def catalogue(self) -> Dict[str, Any]:
        """The legal moves + their JSON format + the named teleport locations. Static public rules."""
        with _quiet():
            actions = self.api.listKnownActions(limited=False)
            fmt = self.api.additionalActionDescriptionString()
            teleports = self.api.listTeleportLocationsDict()
        return {"actions": actions, "action_format": fmt,
                "teleport_locations": teleports,
                "budget_steps": self.budget, "steps_used": self.steps_used()}

    def task(self) -> str:
        """The task description -- legitimately given to the player (it is the goal, not the answer)."""
        tp = (self._last.get("ui", {}) or {}).get("taskProgress") or []
        return tp[0]["description"] if tp else ""

    # ---- the text observation (vision stripped) ---------------------------------------------
    def observe(self) -> Dict[str, Any]:
        """The current text observation for the player. No rendered image; no scorecard."""
        return self._text_obs(self._last)

    def _text_obs(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        ui = dict(obs.get("ui", {}) or {})
        tp = ui.get("taskProgress") or [{}]
        out = {
            "task": tp[0].get("description", ""),
            "task_completed": bool(tp[0].get("completed", False)),
            "steps_used": self.steps_used(),
            "steps_remaining": self.budget_left(),
            "location": ui.get("agentLocation"),
            "last_action_result": ui.get("lastActionMessage"),
            "inventory": ui.get("inventoryObjects"),
            "accessible_objects": ui.get("accessibleEnvironmentObjects"),
            "nearby_objects": _trim_nearby(ui.get("nearbyObjects")),
            "nearby_agents": ui.get("nearbyAgents"),
            "dialog": ui.get("dialog_box"),
            "discovery_feed": ui.get("discoveryFeed"),
        }
        errs = obs.get("errors") or []
        if errs:
            out["errors"] = errs
        return out

    # ---- one move -----------------------------------------------------------------------------
    def act(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Apply one action, tick, and return the resulting text observation. Spends one step."""
        if self.budget_left() <= 0:
            return {"refused": "step budget exhausted -- stop now; the episode is scored from the "
                    "current world state", "steps_used": self.steps_used(), "steps_remaining": 0}
        with _quiet():
            result = self.api.performAgentAction(0, action)
            self.api.tick()
            self._last = self.api.getAgentObservation(0)
        obs = self._text_obs(self._last)
        obs["action_success"] = bool(result.get("success"))
        if result.get("errors"):
            obs["action_errors"] = result["errors"]
        self._log.append({"step": self.steps_used(), "action": action,
                          "success": bool(result.get("success")),
                          "errors": result.get("errors") or []})
        return obs

    # ---- budget / conduct ---------------------------------------------------------------------
    def steps_used(self) -> int:
        with _quiet():
            return int(self.api.getStepCounter())

    def budget_left(self) -> int:
        return max(0, self.budget - self.steps_used())

    def run_log(self) -> List[Dict[str, Any]]:
        return list(self._log)

    # ---- the agent-inaccessible score (harness side only) -------------------------------------
    def scorecard(self) -> Dict[str, Any]:
        """DiscoveryWorld's mechanical scorecard: the process score (`scoreNormalized`, the path
        metric), the per-criterion breakdown, and completion. Deterministic, agent-inaccessible --
        NEVER returned through the player's tool surface."""
        with _quiet():
            cards = self.api.getTaskScorecard() or []
            completed = bool(self.api.areTasksComplete())
        card = cards[0] if cards else {}
        return {
            "score": card.get("score", 0),
            "max_score": card.get("maxScore", 0),
            "score_normalized": float(card.get("scoreNormalized", 0.0)),
            "completed": completed,
            "completed_successfully": bool(card.get("completedSuccessfully", False)),
            "criteria": [
                {"name": c.get("name"), "score": c.get("score"),
                 "max_score": c.get("maxScore"), "completed": c.get("completed")}
                for c in card.get("scoreCard", [])
            ],
            "steps_used": self.steps_used(),
            "budget_steps": self.budget,
        }


def _trim_nearby(nearby: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Drop the verbose boilerplate note and pure-terrain tiles from `nearbyObjects`, keeping the
    direction -> [name, uuid, distance] structure the player navigates by. Token hygiene; it never
    removes an action target (terrain is never one)."""
    if not nearby or "objects" not in nearby:
        return nearby
    out: Dict[str, Any] = {"distance": nearby.get("distance")}
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for direction, items in (nearby.get("objects") or {}).items():
        kept = [{"name": o.get("name"), "uuid": o.get("uuid"), "distance": o.get("distance")}
                for o in items if (o.get("name") or "").split(" ")[0].lower() not in _TERRAIN]
        if kept:
            grouped[direction] = kept
    out["objects"] = grouped
    return out
