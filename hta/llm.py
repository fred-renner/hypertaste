"""The single foundation-model seam. Every LLM call in the system goes through
here, so model assignment and the two `claude -p` invocation modes live in one place.

Two modes:
  * complete(...)  -- CONSTRAINED generation. `claude -p --output-format json
                      --max-turns 1` with no tools. Behaves like a text completion.
                      Used by the task agent (Haiku) and the world-smith (Opus).
  * agentic(...)   -- AGENTIC editing. `claude -p` with Edit/Read/Write tools in a
                      workspace dir. Used by the meta agent (Opus) to rewrite the
                      task agent's code. Never granted Bash, never run where the
                      world source is reachable (airgap).

A deterministic `mock` backend stands in for claude -p so the whole pipeline can be
exercised offline at zero cost. The mock is NOT intelligent; it only makes the
plumbing observable and reproducible.
"""

import json
import re
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .config import Config

# Episodes run concurrently (see task_agent.evaluate), so every claude -p call is
# launched with no stdin: without this the CLI waits 3s per launch for input that
# never comes ("no stdin data received in 3s") -- ~3s x every call of dead latency.
_NO_STDIN = subprocess.DEVNULL

# ---------------------------------------------------------------------------
# Call accounting (so a test run can report calls + $).
# ---------------------------------------------------------------------------
@dataclass
class _Acct:
    calls: int = 0
    cost_usd: float = 0.0
    by_role: Dict[str, int] = field(default_factory=dict)
    by_model: Dict[str, int] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, role: str, model: str, cost: float):
        with self._lock:  # concurrent episodes mutate this from worker threads
            self.calls += 1
            self.cost_usd += float(cost or 0.0)
            self.by_role[role] = self.by_role.get(role, 0) + 1
            self.by_model[model] = self.by_model.get(model, 0) + 1


ACCT = _Acct()


def reset_accounting():
    global ACCT
    ACCT = _Acct()


def accounting() -> dict:
    return {"calls": ACCT.calls, "cost_usd": round(ACCT.cost_usd, 4),
            "by_role": dict(ACCT.by_role), "by_model": dict(ACCT.by_model)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_FENCE = re.compile(r"^```[a-zA-Z0-9_]*\s*|\s*```$", re.MULTILINE)


def strip_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = _FENCE.sub("", t).strip()
    return t


def extract_json(text: str) -> Optional[dict]:
    """Best-effort: parse the last JSON object found in text."""
    t = strip_fences(text)
    try:
        return json.loads(t)
    except Exception:
        pass
    # find last {...} block
    depth = 0
    end = None
    for i in range(len(t) - 1, -1, -1):
        c = t[i]
        if c == "}":
            if depth == 0:
                end = i
            depth += 1
        elif c == "{":
            depth -= 1
            if depth == 0 and end is not None:
                frag = t[i:end + 1]
                try:
                    return json.loads(frag)
                except Exception:
                    end = None
                    depth = 0
    return None


# ---------------------------------------------------------------------------
# CONSTRAINED generation
# ---------------------------------------------------------------------------
def complete(prompt: str, model: str, role: str = "gen", cfg: Optional[Config] = None) -> str:
    cfg = cfg or Config()
    if cfg.backend == "mock":
        out = _mock_complete(prompt, role)
        ACCT.add(role, f"mock:{model}", 0.0)
        return out
    return _real_complete(prompt, model, role, cfg)


def _real_complete(prompt: str, model: str, role: str, cfg: Config) -> str:
    cmd = ["claude", "-p", prompt, "--model", model,
           "--output-format", "json", "--max-turns", "1"]
    last_err = None
    for attempt in range(2):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  stdin=_NO_STDIN, timeout=cfg.call_timeout_s)
            if proc.returncode != 0:
                last_err = f"claude -p exit {proc.returncode}: {proc.stderr[:300]}"
                continue
            obj = json.loads(proc.stdout)
            cost = obj.get("total_cost_usd", 0.0)
            ACCT.add(role, model, cost)
            if obj.get("is_error"):
                last_err = f"claude -p error: {str(obj.get('result'))[:300]}"
                continue
            return strip_fences(obj.get("result", ""))
        except subprocess.TimeoutExpired:
            last_err = "claude -p timeout"
        except json.JSONDecodeError as e:
            last_err = f"bad json from claude -p: {e}"
    raise RuntimeError(f"complete() failed (role={role}, model={model}): {last_err}")


# ---------------------------------------------------------------------------
# AGENTIC editing (meta agent). Real backend only; mock is handled by the caller.
# The argv and result-parsing are factored out so the meta agent can run through the
# SAME airgap flags whether it executes in-process (DirectSandbox) or inside a
# container (DockerSandbox). See hta/dgmh/sandbox.py.
# ---------------------------------------------------------------------------
def agentic_argv(instruction: str, model: str,
                 allowed_tools: Tuple[str, ...], max_turns: int) -> List[str]:
    """The `claude -p` command for an agentic edit, used both on-host and in-container.
    Centralizes the airgap flags: acceptEdits + an explicit tool allowlist (Bash is
    never granted, because it is never placed in `allowed_tools`)."""
    cmd = ["claude", "-p", instruction, "--model", model,
           "--output-format", "json", "--permission-mode", "acceptEdits",
           "--max-turns", str(max_turns)]
    for t in allowed_tools:
        cmd += ["--allowedTools", t]
    return cmd


def agentic_result_from_stdout(stdout: str, role: str, model: str) -> dict:
    """Parse `claude -p --output-format json` stdout into the standard agentic result
    dict and record accounting. Tolerant of leading/trailing log noise (e.g. when the
    JSON is read back from a container's attached stdout). Returns a bad-json error
    dict (and records NO cost) if nothing parseable is found."""
    obj = extract_json(stdout) if (stdout and stdout.strip()) else {}
    if obj is None:
        return {"is_error": True, "result": "bad json", "num_turns": 0, "cost_usd": 0.0}
    cost = obj.get("total_cost_usd", 0.0)
    ACCT.add(role, model, cost)
    return {"is_error": bool(obj.get("is_error")),
            "result": obj.get("result", ""),
            "num_turns": obj.get("num_turns", 0),
            "cost_usd": cost}


def agentic(instruction: str, workdir: str, model: str,
            allowed_tools: Tuple[str, ...], max_turns: int,
            role: str = "meta", cfg: Optional[Config] = None) -> dict:
    cfg = cfg or Config()
    if cfg.backend == "mock":
        raise RuntimeError("agentic() not available in mock backend; caller must handle mock")
    cmd = agentic_argv(instruction, model, allowed_tools, max_turns)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              stdin=_NO_STDIN, cwd=workdir, timeout=cfg.call_timeout_s * 3)
    except subprocess.TimeoutExpired:
        return {"is_error": True, "result": "timeout", "num_turns": 0, "cost_usd": 0.0}
    return agentic_result_from_stdout(proc.stdout, role, model)


# ---------------------------------------------------------------------------
# SINGLE-SESSION EPISODE (task agent). One claude -p session runs a whole world's
# episode, with the probe channel exposed as a narrow stdio-MCP tool. Real only.
# ---------------------------------------------------------------------------
def episode(prompt: str, model: str, mcp_server_argv, server_env, cwd: str,
            allowed_tools, max_turns: int, role: str = "task_episode",
            cfg: Optional[Config] = None, append_system: Optional[str] = None,
            server_name: str = "probe") -> dict:
    cfg = cfg or Config()
    if cfg.backend == "mock":
        raise RuntimeError("episode() not available in mock backend; caller must handle mock")
    # Inline MCP config string -> nothing written to disk that the agent could read. The
    # server name (default "probe") becomes the `mcp__<name>__*` tool prefix; callers that
    # host a different confined world (e.g. the DiscoveryWorld arena) pass their own.
    mcp_cfg = json.dumps({"mcpServers": {server_name: {
        "type": "stdio",
        "command": mcp_server_argv[0],
        "args": list(mcp_server_argv[1:]),
        "env": server_env,  # the hidden rule lives ONLY here, on the server's process
    }}})
    # acceptEdits (not bypassPermissions, which is refused when running as root); the
    # explicit --allowedTools allowlist below is what auto-approves the MCP probe tools.
    cmd = ["claude", "-p", prompt, "--model", model, "--output-format", "json",
           "--mcp-config", mcp_cfg, "--strict-mcp-config",
           "--permission-mode", "acceptEdits",
           "--max-turns", str(max_turns)]
    # Chapter-2 option B: the evolved playbook rides as the player's SYSTEM prompt (it IS the agent),
    # while -p carries only a neutral kickoff. The playbook is read as context, never executed.
    if append_system:
        cmd += ["--append-system-prompt", append_system]
    for t in allowed_tools:
        cmd += ["--allowedTools", t]
    # Belt-and-suspenders: deny every filesystem/network tool so the only channel to
    # the world is the probe MCP tool (airgap).
    cmd += ["--disallowedTools", "Bash", "Read", "Edit", "Write", "WebFetch", "WebSearch", "Glob", "Grep"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd,
                              stdin=_NO_STDIN, timeout=cfg.call_timeout_s * 4)
        obj = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except subprocess.TimeoutExpired:
        return {"is_error": True, "result": "timeout", "num_turns": 0, "cost_usd": 0.0}
    except json.JSONDecodeError:
        return {"is_error": True, "result": (proc.stdout or proc.stderr)[:300],
                "num_turns": 0, "cost_usd": 0.0}
    cost = obj.get("total_cost_usd", 0.0)
    ACCT.add(role, model, cost)  # ONE accounting row for the whole episode
    # On error the JSON has no `result` field; fall back to `subtype` (e.g.
    # "error_max_turns") so the log says *why* instead of an empty message.
    msg = obj.get("result") or obj.get("subtype") or ""
    return {"is_error": bool(obj.get("is_error")), "result": msg,
            "num_turns": obj.get("num_turns", 0), "cost_usd": cost}


# ---------------------------------------------------------------------------
# Deterministic mock backend
# ---------------------------------------------------------------------------
_CTX = re.compile(r"<<CTX>>(.*?)<<CTX>>", re.DOTALL)

def _parse_ctx(prompt: str) -> dict:
    m = _CTX.search(prompt or "")
    if not m:
        return {}
    try:
        return json.loads(m.group(1).strip())
    except Exception:
        return {}


def _mock_complete(prompt: str, role: str) -> str:
    # Neutral stub: the mock backend only makes the plumbing observable. Chapter-2's
    # option-B harness orchestrates via `episode`/`agentic` (the caller handles mock for
    # those); any world-specific `complete` fixtures are (re)introduced at reseed time.
    ctx = _parse_ctx(prompt)
    role = ctx.get("role", role)
    return json.dumps({"note": "mock", "role": role})
