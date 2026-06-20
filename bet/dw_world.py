"""The world, agent-inaccessible. Wraps Ai2's DiscoveryWorld behind a curated,
lean interface and an objective score the agent never sees.

Two integrity rules from the project (CLAUDE.md) hold here:
  * Objective, agent-inaccessible scoring. `agent_view()` returns the task text
    and a done flag only -- never the scorecard. The numeric score lives in
    `scorecard()`, read out-of-band by the harness for measurement.
  * The world is borrowed, not built (DiscoveryWorld, Ai2 2024) and runs headless.

The raw observation is ~7k chars (nearbyObjects dominates with terrain noise);
`agent_view()` curates it to the few hundred chars that actually inform a move,
because every observation rides in the agent's context every turn (token cost).
"""

import contextlib
import io
import os
import sys

# Pure terrain that floods nearbyObjects but never gets acted on -- dropped from
# the curated view to cut tokens. Interactables (instruments, signs, animals,
# statues, doors, ...) are always kept.
_TERRAIN = {"grass", "path", "wall", "floor", "ground", "dirt", "sign post"}
_NEARBY_CAP = 8  # per direction, nearest first


def _locate_discoveryworld() -> None:
    """Put the DiscoveryWorld package on sys.path. Order: already-importable,
    $BET_DW_PATH, then the cloned checkout under bet/discoveryworld.

    Note bet/ is on sys.path (it's the package dir), and the checkout root is
    itself named `discoveryworld` -- so a bare `import discoveryworld` resolves
    it as an empty namespace package and shadows the real one. We validate the
    actual submodule, purge any stale namespace import, and insert the checkout
    root at the FRONT so `discoveryworld/discoveryworld/` wins."""
    try:
        import discoveryworld.DiscoveryWorldAPI  # noqa: F401  -- the real submodule
        return
    except ImportError:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [os.environ.get("BET_DW_PATH"),
                  os.path.join(here, "discoveryworld")]
    for c in candidates:
        if c and os.path.isfile(os.path.join(c, "discoveryworld", "DiscoveryWorldAPI.py")):
            for mod in [m for m in sys.modules if m == "discoveryworld" or m.startswith("discoveryworld.")]:
                del sys.modules[mod]
            sys.path.insert(0, c)
            return
    raise ImportError(
        "DiscoveryWorld not found. Run bet/setup_world.sh, or set BET_DW_PATH "
        "to a discoveryworld checkout.")


class World:
    """One DiscoveryWorld episode: load a scenario, observe, act, score."""

    def __init__(self, scenario: str, difficulty: str, seed: int,
                 max_steps: int, thread_id: int = 1):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        _locate_discoveryworld()
        from discoveryworld.DiscoveryWorldAPI import DiscoveryWorldAPI

        self.scenario = scenario
        self.difficulty = difficulty
        self.seed = seed
        self.max_steps = max_steps
        self.steps_used = 0

        # DiscoveryWorld is chatty on load (sprite/material indices); swallow it
        # so the server's own log stays readable.
        with contextlib.redirect_stdout(io.StringIO()):
            self.api = DiscoveryWorldAPI(threadID=thread_id)
            ok = self.api.loadScenario(scenarioName=scenario,
                                       difficultyStr=difficulty,
                                       randomSeed=seed, numUserAgents=1)
            if not ok:
                raise RuntimeError(
                    f"loadScenario failed: {scenario!r} / {difficulty!r}")
            # World history accumulates a full grid snapshot per tick (~19KB);
            # we never export it, so no-op it to stop the RAM growth + spam.
            self.api.world.saveWorldHistory = lambda: None

    # -- budget ------------------------------------------------------------
    @property
    def budget_remaining(self) -> int:
        return max(0, self.max_steps - self.steps_used)

    # -- the agent-facing, curated view -----------------------------------
    def _raw(self) -> dict:
        with contextlib.redirect_stdout(io.StringIO()):
            return self.api.getAgentObservation(agentIdx=0)["ui"]

    @staticmethod
    def _fmt_obj(o: dict, with_dist: bool = False) -> str:
        s = f"{o.get('name','?')} (uuid {o.get('uuid')})"
        if with_dist and "distance" in o:
            s += f" {o['distance']}t"
        return s

    def agent_view(self) -> dict:
        """The lean observation the agent sees. NO score, by design."""
        ui = self._raw()
        in_dialog = self.api.isAgentInDialog(agentIdx=0)
        loc = ui.get("agentLocation", {})
        view = {
            "step": ui.get("world_steps"),
            "budget_remaining": self.budget_remaining,
            "task": ui.get("taskProgress", [{}])[0].get("description", ""),
            "location": {
                "x": loc.get("x"), "y": loc.get("y"),
                "facing": loc.get("faceDirection"),
                "can_move": loc.get("directions_you_can_move", []),
            },
            "last_action": ui.get("lastActionMessage", ""),
            "in_dialog": in_dialog,
            "inventory": [self._fmt_obj(o) for o in ui.get("inventoryObjects", [])],
            "accessible": [self._fmt_obj(o)
                           for o in ui.get("accessibleEnvironmentObjects", [])
                           if o.get("name") not in _TERRAIN],
        }
        if in_dialog:
            db = ui.get("dialog_box", {})
            view["dialog"] = {
                "npc_says": db.get("dialogIn", ""),
                "options": db.get("dialogOptions", {}),
            }
        else:
            nearby = {}
            for direction, payload in ui.get("nearbyObjects", {}).get("objects", {}).items():
                items = [self._fmt_obj(o, with_dist=True) for o in payload
                         if o.get("name") not in _TERRAIN]
                if items:
                    nearby[direction] = items[:_NEARBY_CAP]
            view["nearby"] = nearby
        return view

    def actions(self) -> dict:
        with contextlib.redirect_stdout(io.StringIO()):
            return self.api.listKnownActions(limited=False)

    def locations(self) -> dict:
        with contextlib.redirect_stdout(io.StringIO()):
            return self.api.listTeleportLocationsDict()

    # -- acting ------------------------------------------------------------
    def act(self, action: dict) -> dict:
        """Perform one action + tick. Returns {result, done}. Spends one step."""
        with contextlib.redirect_stdout(io.StringIO()):
            result = self.api.performAgentAction(agentIdx=0, actionJSON=action)
            self.api.tick()
        self.steps_used += 1
        done = self.api.areTasksComplete()
        msg = result if isinstance(result, str) else (
            result.get("message") if isinstance(result, dict) else str(result))
        return {"result": msg or "", "done": bool(done)}

    # -- the objective score, out-of-band (harness only) -------------------
    def scorecard(self) -> dict:
        with contextlib.redirect_stdout(io.StringIO()):
            sc = self.api.getTaskScorecard()
        card = sc[0] if isinstance(sc, list) else sc
        crit = card.get("criticalQuestions", []) or []
        return {
            "task": card.get("taskName"),
            "completed": bool(card.get("completed")),
            "completed_successfully": bool(card.get("completedSuccessfully")),
            "process_score": float(card.get("scoreNormalized", 0.0) or 0.0),
            "score": card.get("score"),
            "max_score": card.get("maxScore"),
            "n_critical_questions": len(crit),
            "steps_used": self.steps_used,
        }
