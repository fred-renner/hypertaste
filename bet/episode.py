"""Run one episode: one (arm, scenario, seed) on one world, scored.

Flow:
  1. Start the world server (separate process; holds the world).
  2. Build a clean agent workdir containing ONLY the client (dw.py + rpc.py) --
     the world's code is never placed where the agent can read it (the airgap).
  3. Drive the agent:
       - real: a native Haiku `claude -p` session, given the fixed KICKOFF, the
         arm's decision prose as system prompt, and Bash locked to `python dw.py`.
       - mock: a deterministic policy (offline, free) that exercises the same
         socket protocol so the whole pipe is testable without a model.
  4. Read the objective scorecard out-of-band (privileged socket command).
  5. Shut the server down.

The agent's only difference between arms is the system prompt; everything else
(the harness) is held fixed -- that is the experiment.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from rpc import call  # noqa: E402
from prompts import KICKOFF, load_arm  # noqa: E402

# Bash is granted ONLY for the client; every file/network/escape tool is denied.
# This is the soft airgap (in-process tool confinement). The world source isn't
# in the agent's cwd either, so the easy path is the only path.
_ALLOWED = ("Bash(python dw.py:*)", "Bash(python3 dw.py:*)")
_DISALLOWED = ("Read", "Write", "Edit", "MultiEdit", "NotebookEdit",
               "Glob", "Grep", "WebFetch", "WebSearch", "Task")
_MODELS = {"haiku": "claude-haiku-4-5-20251001"}


def _wait_ready(sock_path: str, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if call(sock_path, {"cmd": "ping"}, timeout=2.0).get("pong"):
                return
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("world server did not become ready")


def _start_server(sock_path, scenario, difficulty, seed, max_steps, thread_id, scratch):
    # DiscoveryWorld writes frame/log dirs (video/, logs/) relative to cwd; run
    # the server in a throwaway scratch dir so those artifacts never touch the repo.
    proc = subprocess.Popen(
        [sys.executable, os.path.join(_HERE, "server.py"),
         "--socket", sock_path, "--scenario", scenario,
         "--difficulty", difficulty, "--seed", str(seed),
         "--max-steps", str(max_steps), "--thread-id", str(thread_id)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=scratch)
    _wait_ready(sock_path)
    return proc


def _agent_workdir(sock_path) -> str:
    d = tempfile.mkdtemp(prefix="bet_agent_")
    for f in ("dw.py", "rpc.py"):
        shutil.copy(os.path.join(_HERE, f), os.path.join(d, f))
    return d


# --------------------------------------------------------------------------
# Real agent: a native Haiku claude -p session.
# --------------------------------------------------------------------------
def _run_real(arm, sock_path, workdir, model, max_turns, timeout_s):
    system = load_arm(arm)
    cmd = ["claude", "-p", KICKOFF,
           "--model", _MODELS.get(model, model),
           "--append-system-prompt", system,
           "--output-format", "json",
           "--permission-mode", "acceptEdits",
           "--max-turns", str(max_turns)]
    for t in _ALLOWED:
        cmd += ["--allowedTools", t]
    for t in _DISALLOWED:
        cmd += ["--disallowedTools", t]
    env = dict(os.environ, BET_SOCKET=sock_path)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, cwd=workdir,
                              env=env, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"cost_usd": 0.0, "num_turns": 0, "error": "agent timeout"}
    try:
        obj = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        return {"cost_usd": 0.0, "num_turns": 0,
                "error": (proc.stdout or proc.stderr)[:300]}
    return {"cost_usd": float(obj.get("total_cost_usd", 0.0) or 0.0),
            "num_turns": obj.get("num_turns", 0),
            "is_error": bool(obj.get("is_error")),
            "result": (obj.get("result") or obj.get("subtype") or "")[:1500]}


# --------------------------------------------------------------------------
# Mock agent: deterministic, offline, free. Exercises the real socket protocol
# so server/client/budget/scoring are all tested without a model. NOT smart --
# it only makes the plumbing observable (mirrors hta's mock backend).
# --------------------------------------------------------------------------
def _run_mock(arm, sock_path, max_steps, seed):
    import random
    rng = random.Random(seed)
    locs = list(call(sock_path, {"cmd": "locations"}).get("locations", {}).keys())
    turns = 0
    for _ in range(max_steps + 5):
        obs = call(sock_path, {"cmd": "observe"}).get("obs", {})
        if obs.get("budget_remaining", 0) <= 0:
            break
        if obs.get("in_dialog"):
            opts = list((obs.get("dialog", {}).get("options") or {}).keys())
            choice = int(opts[0]) if opts and opts[0].isdigit() else 1
            call(sock_path, {"cmd": "act", "action": {"chosen_dialog_option_int": choice}})
        elif locs and turns % 3 == 0:
            call(sock_path, {"cmd": "act", "action": {
                "action": "TELEPORT_TO_LOCATION", "arg1": rng.choice(locs)}})
        else:
            # READ whatever is in reach, else a no-op move.
            acc = obs.get("accessible") or []
            uuid = None
            if acc:
                # "name (uuid 123)" -> 123
                try:
                    uuid = int(acc[0].split("uuid")[1].strip(" )"))
                except Exception:
                    uuid = None
            if uuid is not None:
                call(sock_path, {"cmd": "act", "action": {"action": "READ", "arg1": uuid}})
            else:
                call(sock_path, {"cmd": "act", "action": {
                    "action": "MOVE_DIRECTION", "arg1": rng.choice(["north", "east", "south", "west"])}})
        turns += 1
    return {"cost_usd": 0.0, "num_turns": turns, "result": "(mock policy)"}


# --------------------------------------------------------------------------
def run_episode(arm, scenario, difficulty, seed, *, backend="mock",
                max_steps=30, model="haiku", thread_id=1,
                max_turns=None, timeout_s=1800):
    """Run one episode and return a result dict (arm, scores, cost)."""
    if max_turns is None:
        max_turns = max_steps * 3 + 20
    tmp = tempfile.mkdtemp(prefix="bet_sock_")
    sock_path = os.path.join(tmp, "world.sock")
    server = _start_server(sock_path, scenario, difficulty, seed, max_steps,
                           thread_id, scratch=tmp)
    workdir = None
    try:
        if backend == "real":
            workdir = _agent_workdir(sock_path)
            agent = _run_real(arm, sock_path, workdir, model, max_turns, timeout_s)
        elif backend == "mock":
            agent = _run_mock(arm, sock_path, max_steps, seed)
        else:
            raise ValueError(f"unknown backend {backend!r}")
        scorecard = call(sock_path, {"cmd": "scorecard"}).get("scorecard", {})
        return {
            "arm": arm, "backend": backend, "scenario": scenario,
            "difficulty": difficulty, "seed": seed, "max_steps": max_steps,
            "scorecard": scorecard, "agent": agent,
        }
    finally:
        try:
            call(sock_path, {"cmd": "shutdown"}, timeout=2.0)
        except Exception:
            pass
        server.terminate()
        try:
            server.wait(timeout=10)
        except Exception:
            server.kill()
        if workdir:
            shutil.rmtree(workdir, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)
