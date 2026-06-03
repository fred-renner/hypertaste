"""Stdio MCP server exposing ONE WILT world as narrow probe tools.

Run as a child of a `claude -p` episode session (single-session task-agent mode).
It owns the hidden rule -- compiled in-memory from the server-only env var
HTA_RULE_SRC -- and exposes exactly three tools to the session:

    probe(x, y, z)      -> {"result": bool, "remaining": int}
    remaining()         -> {"remaining": int}
    submit_guess(rule)  -> {"accepted": bool}   # accepted == parseable/safe, NOT correct

Airgap: the session speaks only JSON-RPC over stdio. It cannot read this process's
env/argv/memory (it has no filesystem tools), so it can never see HTA_RULE_SRC. The
probe trajectory + final guess are appended to HTA_TRAJ_PATH -- a path the PARENT
harness passes and reads after the session ends; the agent session cannot read it.
Scoring lives in the parent (hta.world.engine.WiltWorld.score_guess), never here.

This is a minimal hand-rolled MCP server (the `mcp` SDK is not installed): just
`initialize`, `notifications/initialized`, `tools/list`, `tools/call` over stdin/stdout,
one JSON object per line. Pure standard library, no third-party deps.
"""

import json
import os
import sys

# Support both `python -m hta.world.probe_server` and direct-path execution.
try:
    from .grammar import compile_rule, validate_lambda
    from .channel import ProbeChannel
except ImportError:  # pragma: no cover - direct path execution
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from hta.world.grammar import compile_rule, validate_lambda
    from hta.world.channel import ProbeChannel

PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "probe",
        "description": ("Submit a test case (three numbers) to the hidden rule. Returns the "
                        "rule's boolean for that case and how many probes remain. Use this to "
                        "gather evidence about the hidden rule."),
        "inputSchema": {
            "type": "object",
            "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"}},
            "required": ["x", "y", "z"],
        },
    },
    {
        "name": "remaining",
        "description": "How many probes remain in this episode.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "submit_guess",
        "description": ("Submit your final answer: a Python lambda over x, y, z that returns a "
                        "bool, e.g. 'lambda x, y, z: x < y < z'. Ends the episode. Submit exactly "
                        "once, when you are confident."),
        "inputSchema": {
            "type": "object",
            "properties": {"rule": {"type": "string"}},
            "required": ["rule"],
        },
    },
]


class _World:
    def __init__(self):
        src = os.environ.get("HTA_RULE_SRC", "")
        if not validate_lambda(src):
            raise SystemExit("probe_server: invalid or missing HTA_RULE_SRC")
        self.channel = ProbeChannel(compile_rule(src), int(os.environ.get("HTA_MAX_PROBES", "30")))
        self.traj_path = os.environ.get("HTA_TRAJ_PATH")
        self.guess = None

    def _append(self, record):
        if not self.traj_path:
            return
        with open(self.traj_path, "a") as f:
            f.write(json.dumps(record) + "\n")

    def probe(self, args):
        label = self.channel.probe([args["x"], args["y"], args["z"]])
        rec = self.channel.history()[-1]
        self._append({"type": "probe", **rec})
        return {"result": bool(label), "remaining": self.channel.remaining()}

    def remaining(self, args):
        return {"remaining": self.channel.remaining()}

    def submit_guess(self, args):
        rule = (args.get("rule") or "").strip()
        self.guess = rule
        accepted = bool(validate_lambda(rule))
        self._append({"type": "guess", "rule": rule, "accepted": accepted})
        return {"accepted": accepted}


def _send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _result(mid, payload, is_error=False):
    _send({"jsonrpc": "2.0", "id": mid,
           "result": {"content": [{"type": "text", "text": json.dumps(payload)}],
                      "isError": is_error}})


def main():
    world = _World()
    dispatch = {"probe": world.probe, "remaining": world.remaining, "submit_guess": world.submit_guess}
    for line in sys.stdin:
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
            _send({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "probe", "version": "1.0"}}})
        elif method == "notifications/initialized":
            continue  # notification: no response
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {}) or {}
            fn = dispatch.get(name)
            if fn is None:
                _result(mid, {"error": f"unknown tool {name!r}"}, is_error=True)
                continue
            try:
                _result(mid, fn(args))
            except Exception as e:  # noqa: BLE001 - report tool errors to the session
                _result(mid, {"error": str(e)}, is_error=True)
        elif mid is not None:
            _send({"jsonrpc": "2.0", "id": mid,
                   "error": {"code": -32601, "message": f"method not found: {method}"}})
        # else: a notification we don't handle -> ignore


if __name__ == "__main__":
    main()
