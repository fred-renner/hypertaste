"""Stdio MCP server exposing ONE Chapter-2 episode as the confined orchestration tools — the
frozen substrate of the model-orchestrated harness (option B, RESET_DESIGN.md -> "The harness
spec"). It is a thin wrapper: every tool delegates to an `EpisodeState` (hta/ch2/episode_state.py),
which holds the hidden world (passed in-memory via the server-only env `HTA_WORLD`/`HTA_HSTAR`) and
all the load-bearing logic. The player speaks only JSON-RPC over stdio with no filesystem tools, so
it can never read this process's env (the seed) — it learns the world solely by probing. That tool
confinement IS the airgap.

Two roles, gated by the toolset the wrapper offers (HTA_ROLE):
  * **top**     — probe, remaining, world_map, mem_read, mem_patch, submit_map, spawn.
  * **worker**  — probe, remaining only. A spawn launches a FRESH worker session (a nested
                  `claude -p`) against an isolated copy of the world with a carved sub-budget; it
                  sees only its task + budget, never the playbook/scratchpad/top context. Depth = 1
                  (workers have no spawn).

The episode result (log, scratchpad, submission, spawns) is written to `HTA_RESULT_PATH` after every
mutating call — the dropbox the PARENT process reads once the session ends (the loop for a top, the
spawn handler for a worker). Scoring lives in the parent / `EpisodeState.score`, never here.

A minimal hand-rolled MCP server (stdlib only): initialize / notifications/initialized / tools/list
/ tools/call, one JSON object per line. The framing loop is `serve(...)`, which takes injectable
streams + a worker runner so the dispatch, the role airgap, and the spawn carve-out are all
exercised offline without a live `claude -p` (tests/test_probe_server.py).
"""

import json
import os
import sys
import tempfile

try:
    from .episode_state import EpisodeState, state_from_env, state_to_env
except ImportError:  # pragma: no cover - direct path execution
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from hta.ch2.episode_state import EpisodeState, state_from_env, state_to_env

PROTOCOL_VERSION = "2024-11-05"

# Fixed boilerplate wrapping the top-authored task. "How to instruct a worker" stays emergent (the
# top writes {task}); only the confinement + the report contract are fixed substrate.
WORKER_WRAPPER = (
    "You are a probe worker deployed to investigate part of a hidden world. Task: {task}\n\n"
    "You may call `probe(index)` up to your budget of {budget} (cost-weighted) and `remaining()`. "
    "You have no other tools and no other context. When done (or out of budget), STOP and write a "
    "short report of what you found — list the cell index -> value pairs you observed and any "
    "structure you inferred. Be terse and factual.")

# ---- tool schemas (advertised by tools/list; the player reads the descriptions) ----
_T_PROBE = {"name": "probe",
            "description": ("Reveal the hidden value (a small integer) at one cell, charging its "
                            "cost against the global budget. Only cells world_map marks probeable "
                            "can be probed; coverage cells are reconstructed, never probed. "
                            "Returns {value, remaining, cost}."),
            "inputSchema": {"type": "object", "properties": {"index": {"type": "integer"}},
                            "required": ["index"]}}
_T_REMAINING = {"name": "remaining", "description": "Cost budget left in this episode.",
                "inputSchema": {"type": "object", "properties": {}}}
_T_WORLD_MAP = {"name": "world_map",
                "description": ("The public rules of the game: the map's structure, the cell "
                                "layout with costs and roles, and the deterministic value law. "
                                "The hidden values are what you probe. probe()/submit_map() use "
                                "the `col` fields here."),
                "inputSchema": {"type": "object", "properties": {}}}
_T_MEM_READ = {"name": "mem_read", "description": "Read your within-episode scratchpad.",
               "inputSchema": {"type": "object", "properties": {}}}
_T_MEM_PATCH = {"name": "mem_patch",
                "description": ("Incrementally edit the scratchpad. Omit `find` to append `replace`; "
                                "give `find` to replace its first occurrence with `replace` (empty "
                                "replace deletes). Use it to track threads, consolidate worker "
                                "reports, and revise beliefs as you go."),
                "inputSchema": {"type": "object",
                                "properties": {"find": {"type": "string"}, "replace": {"type": "string"}}}}
_T_SUBMIT = {"name": "submit_map",
             "description": ("End the episode with your reconstruction: an object mapping cell `col` "
                             "-> value for every cell you can determine (coverage cells earn the "
                             "score). Submit once, when further probing is not worth its cost."),
             "inputSchema": {"type": "object",
                             "properties": {"values": {"type": "object"}}, "required": ["values"]}}
_T_SPAWN = {"name": "spawn",
            "description": ("Deploy ONE fresh probe worker with a task you write and a share of your "
                            "budget (<= remaining; unused returns). It investigates independently and "
                            "reports back {observations, report, used}; its probes count toward your "
                            "coverage. It sees only your task + its budget."),
            "inputSchema": {"type": "object",
                            "properties": {"task": {"type": "string"}, "budget": {"type": "integer"}},
                            "required": ["task", "budget"]}}

TOOLS_TOP = [_T_PROBE, _T_REMAINING, _T_WORLD_MAP, _T_MEM_READ, _T_MEM_PATCH, _T_SUBMIT, _T_SPAWN]
TOOLS_WORKER = [_T_PROBE, _T_REMAINING]


# ---------------------------------------------------------------------------
# The real spawn worker: a nested `claude -p` against an isolated copy of the world. Real backend
# only; injected as a seam so the framing/airgap is testable offline.
# ---------------------------------------------------------------------------
def run_worker(task: str, budget: int, world_env: dict, log_path=None) -> dict:
    """Run a confined worker session and return {observations, used, report}. The worker gets a
    fresh EpisodeState (same world, sub-budget) in its own probe-server process; we read its dropbox
    after it exits. Real backend only."""
    from .. import llm
    from ..config import Config
    cfg = Config()  # reads HTA_BACKEND / HTA_TASK_MODEL from the server's env
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    fd, result_path = tempfile.mkstemp(prefix="hta_worker_", suffix=".json")
    os.close(fd)
    env = dict(world_env)
    env.update({"HTA_BUDGET": str(int(budget)), "HTA_ROLE": "worker",
                "HTA_RESULT_PATH": result_path})
    prompt = WORKER_WRAPPER.format(task=task, budget=int(budget))
    res = llm.episode(prompt=prompt, model=cfg.task_model,
                      mcp_server_argv=[sys.executable, "-m", "hta.ch2.probe_server"],
                      server_env=env, cwd=repo_root,
                      allowed_tools=("mcp__probe__probe", "mcp__probe__remaining"),
                      max_turns=int(budget) * 2 + 6, role="worker", cfg=cfg)
    obs, used = [], 0
    try:
        with open(result_path) as f:
            r = json.load(f)
        obs, used = r.get("observations", []), r.get("used", 0)
    except (OSError, json.JSONDecodeError):
        pass
    finally:
        try:
            os.remove(result_path)
        except OSError:
            pass
    return {"observations": obs, "used": used, "report": (res.get("result") or "")[:1500]}


# ---------------------------------------------------------------------------
# JSON-RPC framing + dispatch. Pure given (state, role, runner, streams) — no global I/O.
# ---------------------------------------------------------------------------
def _send(out, obj):
    out.write(json.dumps(obj) + "\n")
    out.flush()


def _result(out, mid, payload, is_error=False):
    _send(out, {"jsonrpc": "2.0", "id": mid,
                "result": {"content": [{"type": "text", "text": json.dumps(payload)}],
                           "isError": is_error}})


def serve(state: EpisodeState, role: str, instream, outstream,
          result_path=None, world_env=None, runner=run_worker):
    """The MCP framing loop over the given streams. `role` selects the toolset (the airgap);
    `runner` runs a spawn's worker (injected in tests). State mutations are flushed to
    `result_path` so the parent process can read the episode result after the session ends."""
    tools = TOOLS_TOP if role == "top" else TOOLS_WORKER
    names = {t["name"] for t in tools}

    def persist():
        if result_path:
            with open(result_path, "w") as f:
                json.dump(state.result(), f)

    def call(name, args):
        if name == "probe":
            r = state.probe(args.get("index"))
            persist()
            return r
        if name == "remaining":
            return state.remaining()
        if name == "world_map":
            return state.world_map()
        if name == "mem_read":
            return state.mem_read()
        if name == "mem_patch":
            r = state.mem_patch(args.get("find"), args.get("replace", ""))
            persist()
            return r
        if name == "submit_map":
            r = state.submit_map(args.get("values"))
            persist()
            return r
        if name == "spawn":
            granted = state.grant_spawn(args.get("budget"))
            if granted <= 0:
                return {"observations": [], "report": "", "used": 0,
                        "remaining": state.remaining_cost(), "error": "no budget to grant"}
            w = runner(str(args.get("task", "")), granted, world_env or {})
            r = state.commit_spawn(str(args.get("task", "")), w.get("observations"),
                                   w.get("used", 0), report=w.get("report", ""))
            persist()
            return r
        raise ValueError(f"unknown or unauthorized tool {name!r}")

    for line in instream:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        mid = msg.get("id")
        method = msg.get("method")
        params = msg.get("params", {}) or {}
        if method == "initialize":
            _send(outstream, {"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "probe", "version": "2.0"}}})
        elif method == "notifications/initialized":
            continue  # notification: no response
        elif method == "tools/list":
            _send(outstream, {"jsonrpc": "2.0", "id": mid, "result": {"tools": tools}})
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {}) or {}
            if name not in names:
                _result(outstream, mid, {"error": f"unknown or unauthorized tool {name!r}"},
                        is_error=True)
                continue
            try:
                _result(outstream, mid, call(name, args))
            except Exception as e:  # noqa: BLE001 - report tool errors back to the session
                _result(outstream, mid, {"error": str(e)}, is_error=True)
        elif mid is not None:
            _send(outstream, {"jsonrpc": "2.0", "id": mid,
                              "error": {"code": -32601, "message": f"method not found: {method}"}})
        # else: an unhandled notification -> ignore


def main():
    state = state_from_env(os.environ)
    role = os.environ.get("HTA_ROLE", "top")
    result_path = os.environ.get("HTA_RESULT_PATH")
    # The world env to hand any spawned worker (same hidden seed, the wrapper re-budgets it).
    world_env = {"HTA_WORLD": os.environ["HTA_WORLD"], "HTA_HSTAR": os.environ["HTA_HSTAR"],
                 "HTA_BACKEND": os.environ.get("HTA_BACKEND", "real"),
                 "HTA_TASK_MODEL": os.environ.get("HTA_TASK_MODEL", "haiku")}
    serve(state, role, sys.stdin, sys.stdout, result_path=result_path, world_env=world_env)


if __name__ == "__main__":
    main()
