"""Stdio MCP server exposing ONE Chapter-2 tape as narrow probe tools.

Run as a child of a `claude -p` episode session (single-session task-agent mode). It owns
the hidden tape — passed in-memory via the server-only env var HTA_TAPE (a JSON array of
ints) — and exposes exactly three tools to the session:

    probe(index)        -> {"value": int, "remaining": int}
    remaining()         -> {"remaining": int}
    submit_map(values)  -> {"accepted": bool}   # accepted == right length, NOT correct

Airgap: the session speaks only JSON-RPC over stdio with no filesystem tools, so it can
never read this process's env (the answer key) — it learns the tape only by probing.
The trajectory + final reconstruction are appended to HTA_TRAJ_PATH, which the PARENT
harness reads after the session ends; scoring lives in the parent (TapeWorld.score),
never here.

A minimal hand-rolled MCP server (stdlib only), mirroring hta/world/probe_server.py.
"""

import json
import os
import sys

PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "probe",
        "description": ("Reveal the hidden color (an integer) at one tape cell. Returns that "
                        "cell's value and how many probes remain. Use this to gather evidence "
                        "about each segment's pattern."),
        "inputSchema": {
            "type": "object",
            "properties": {"index": {"type": "integer"}},
            "required": ["index"],
        },
    },
    {
        "name": "remaining",
        "description": "How many probes remain in this episode.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "submit_map",
        "description": ("Submit your final reconstruction: a JSON array of the color (integer) "
                        "for EVERY cell of the tape, in order. Ends the episode. Submit exactly "
                        "once, when you have predicted every cell."),
        "inputSchema": {
            "type": "object",
            "properties": {"values": {"type": "array", "items": {"type": "integer"}}},
            "required": ["values"],
        },
    },
]


class _World:
    def __init__(self):
        try:
            self.tape = list(json.loads(os.environ.get("HTA_TAPE", "")))
        except Exception:
            raise SystemExit("probe_server: invalid or missing HTA_TAPE")
        self.max = int(os.environ.get("HTA_BUDGET", "8"))
        self.used = 0
        self.traj_path = os.environ.get("HTA_TRAJ_PATH")
        self.recon = None

    def _append(self, record):
        if not self.traj_path:
            return
        with open(self.traj_path, "a") as f:
            f.write(json.dumps(record) + "\n")

    def probe(self, args):
        idx = args.get("index")
        if not isinstance(idx, int) or isinstance(idx, bool) or self.used >= self.max:
            self._append({"type": "probe", "index": idx, "value": None, "malformed": True})
            return {"value": None, "remaining": max(0, self.max - self.used)}
        if not (0 <= idx < len(self.tape)):
            self.used += 1
            self._append({"type": "probe", "index": idx, "value": None, "malformed": True})
            return {"value": None, "remaining": self.max - self.used}
        self.used += 1
        val = int(self.tape[idx])
        self._append({"type": "probe", "index": idx, "value": val, "malformed": False})
        return {"value": val, "remaining": self.max - self.used}

    def remaining(self, args):
        return {"remaining": max(0, self.max - self.used)}

    def submit_map(self, args):
        vals = args.get("values")
        ok = isinstance(vals, list) and len(vals) == len(self.tape) and all(
            isinstance(v, int) and not isinstance(v, bool) for v in vals)
        self.recon = list(vals) if isinstance(vals, list) else None
        self._append({"type": "submit", "values": self.recon, "accepted": bool(ok)})
        return {"accepted": bool(ok)}


def _send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _result(mid, payload, is_error=False):
    _send({"jsonrpc": "2.0", "id": mid,
           "result": {"content": [{"type": "text", "text": json.dumps(payload)}],
                      "isError": is_error}})


def main():
    world = _World()
    dispatch = {"probe": world.probe, "remaining": world.remaining, "submit_map": world.submit_map}
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
                "serverInfo": {"name": "map_probe", "version": "1.0"}}})
        elif method == "notifications/initialized":
            continue
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


if __name__ == "__main__":
    main()
