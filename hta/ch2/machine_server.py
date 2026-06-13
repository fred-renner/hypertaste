"""Stdio-MCP server exposing ONE machine-world episode as the confined body (the analogue of
`probe_server.py` for kit v1). A thin wrapper: every tool delegates to a `MachineEpisode`
(hta/ch2/machine_state.py), which holds the hidden machine (passed in-memory via the server-only env
`HTA_MACHINE`) and all the load-bearing logic. The player speaks only JSON-RPC over stdio with no
filesystem tools, so it can never read this process's env — it learns the machine solely by probing.
That tool confinement IS the airgap.

One role for instance 0 (no spawn yet): probe, remaining, machine_map, mem_read, mem_patch, submit.
The episode result (log, scratchpad, submission) is flushed to `HTA_RESULT_PATH` after every mutating
call — the dropbox the parent process reads once the session ends. Scoring lives in the parent /
`MachineEpisode.score`, never here.

A minimal hand-rolled MCP server (stdlib only); the framing loop `serve(...)` takes injectable
streams so dispatch is exercised offline without a live `claude -p` (tests/test_machine.py).
"""

import json
import os
import sys

try:
    from .machine_state import MachineEpisode, machine_from_env
except ImportError:  # pragma: no cover - direct path execution
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from hta.ch2.machine_state import MachineEpisode, machine_from_env

PROTOCOL_VERSION = "2024-11-05"

_T_PROBE = {"name": "probe",
            "description": ("Set one output's scalar input and read its value, spending one unit of "
                            "budget. Probing earns NOTHING toward your score — it only buys "
                            "understanding. Returns {value, remaining}."),
            "inputSchema": {"type": "object",
                            "properties": {"output": {"type": "integer"}, "input": {"type": "integer"}},
                            "required": ["output", "input"]}}
_T_REMAINING = {"name": "remaining", "description": "Probe budget left in this episode.",
                "inputSchema": {"type": "object", "properties": {}}}
_T_MACHINE_MAP = {"name": "machine_map",
                  "description": ("The public rules of the game: each output's input domain and "
                                  "weight, the value-law vocabulary (constant / affine / table), and "
                                  "the scoring contract. The laws and parameters are hidden — probe "
                                  "to learn them."),
                  "inputSchema": {"type": "object", "properties": {}}}
_T_MEM_READ = {"name": "mem_read", "description": "Read your within-episode scratchpad.",
               "inputSchema": {"type": "object", "properties": {}}}
_T_MEM_PATCH = {"name": "mem_patch",
                "description": ("Incrementally edit the scratchpad. Omit `find` to append `replace`; "
                                "give `find` to replace its first occurrence (empty replace deletes). "
                                "Track which outputs you have identified and how."),
                "inputSchema": {"type": "object",
                                "properties": {"find": {"type": "string"}, "replace": {"type": "string"}}}}
_T_SUBMIT = {"name": "submit",
             "description": ("End the episode with one model per output, an object mapping the output "
                             "index to a law: {\"law\":\"const\",\"c\":int} | "
                             "{\"law\":\"affine\",\"a\":int,\"b\":int} | "
                             "{\"law\":\"table\",\"values\":{\"<input>\":int,...}} | "
                             "{\"law\":\"abstain\"}. Omitted outputs are graded as abstain. Submit "
                             "once, when further probing is not worth its cost."),
             "inputSchema": {"type": "object",
                             "properties": {"models": {"type": "object"}}, "required": ["models"]}}

TOOLS = [_T_PROBE, _T_REMAINING, _T_MACHINE_MAP, _T_MEM_READ, _T_MEM_PATCH, _T_SUBMIT]


def _send(out, obj):
    out.write(json.dumps(obj) + "\n")
    out.flush()


def _result(out, mid, payload, is_error=False):
    _send(out, {"jsonrpc": "2.0", "id": mid,
                "result": {"content": [{"type": "text", "text": json.dumps(payload)}],
                           "isError": is_error}})


def serve(episode: MachineEpisode, instream, outstream, result_path=None):
    """The MCP framing loop over the given streams. State mutations are flushed to `result_path` so
    the parent process can read the episode result after the session ends."""
    names = {t["name"] for t in TOOLS}

    def persist():
        if result_path:
            with open(result_path, "w") as f:
                json.dump(episode.result(), f)

    def call(name, args):
        if name == "probe":
            r = episode.probe(args.get("output"), args.get("input"))
            persist()
            return r
        if name == "remaining":
            return episode.remaining()
        if name == "machine_map":
            return episode.machine_map()
        if name == "mem_read":
            return episode.mem_read()
        if name == "mem_patch":
            r = episode.mem_patch(args.get("find"), args.get("replace", ""))
            persist()
            return r
        if name == "submit":
            r = episode.submit(args.get("models"))
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
                "serverInfo": {"name": "probe", "version": "1.0"}}})
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            _send(outstream, {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
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


def main():
    episode = machine_from_env(os.environ)
    result_path = os.environ.get("HTA_RESULT_PATH")
    serve(episode, sys.stdin, sys.stdout, result_path=result_path)


if __name__ == "__main__":
    main()
