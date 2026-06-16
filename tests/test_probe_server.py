"""Tests for the stdio-MCP probe server (hta/_trail/probe_server.py) — the frozen wrapper. We drive
its JSON-RPC framing loop over in-memory streams with an injected spawn runner, so the protocol, the
role airgap (which toolset each role is offered), and the spawn carve-out are all exercised offline
with no live `claude -p`. The heavy logic lives in EpisodeState (tested separately); here we prove
the wrapper translates faithfully and confines correctly.
"""

import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta._trail import anchor  # noqa: E402
from hta._trail.episode_state import EpisodeState  # noqa: E402
from hta._trail import probe_server as ps  # noqa: E402

SPEC = anchor.TrailSpec("trail-small", R=8, K=2, Ld=2, Lv=9, trailhead=0,
                        waypoints=(1, 2), landmarks=((3, 4), (3, 4)), budget=3)
HSTAR = (1, 0, 1, 0, 1, 0, 1, 0)


def drive(role, requests, runner=None, result_path=None):
    """Feed JSON-RPC request dicts through serve() and return the parsed response objects."""
    st = EpisodeState(SPEC, HSTAR)
    instream = [json.dumps(r) + "\n" for r in requests]
    out = io.StringIO()
    kwargs = {"result_path": result_path, "world_env": {}}
    if runner is not None:
        kwargs["runner"] = runner
    ps.serve(st, role, instream, out, **kwargs)
    return st, [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]


def tool_payload(resp):
    """Unwrap a tools/call response -> the tool's JSON payload."""
    return json.loads(resp["result"]["content"][0]["text"])


def probeable_clearing(st):
    return next(i for i, c in enumerate(st.cells) if c[0] == "direct")


def test_initialize_and_tools_list_by_role():
    _, resp = drive("top", [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
                             "params": {"protocolVersion": "2024-11-05"}},
                            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])
    assert resp[0]["result"]["protocolVersion"] == "2024-11-05"
    assert resp[0]["result"]["serverInfo"]["name"] == "probe"
    top_tools = {t["name"] for t in resp[1]["result"]["tools"]}
    assert top_tools == {"probe", "remaining", "world_map", "mem_read", "mem_patch",
                         "submit_map", "spawn"}
    _, wresp = drive("worker", [{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}])
    assert {t["name"] for t in wresp[0]["result"]["tools"]} == {"probe", "remaining"}


def test_notification_initialized_gets_no_response():
    _, resp = drive("top", [{"jsonrpc": "2.0", "method": "notifications/initialized"}])
    assert resp == []                                       # a notification: silent


def test_probe_call_returns_value_and_persists_result():
    st0 = EpisodeState(SPEC, HSTAR)
    col = probeable_clearing(st0)
    fd, rp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        st, resp = drive("top", [{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                  "params": {"name": "probe", "arguments": {"index": col}}}],
                         result_path=rp)
        payload = tool_payload(resp[0])
        assert payload["value"] == anchor.cell_value(SPEC, st.cells[col], HSTAR)
        assert payload["remaining"] == SPEC.budget - 1
        with open(rp) as f:                                # the dropbox the parent reads
            persisted = json.load(f)
        assert persisted["log"][0]["col"] == col
    finally:
        os.remove(rp)


def test_worker_cannot_call_top_only_tools():
    # world_map / spawn are not in the worker's offered set -> unauthorized, never dispatched.
    _, resp = drive("worker", [{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                "params": {"name": "world_map", "arguments": {}}},
                               {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                "params": {"name": "spawn",
                                           "arguments": {"task": "x", "budget": 1}}}])
    assert resp[0]["result"]["isError"] and "unauthorized" in tool_payload(resp[0])["error"]
    assert resp[1]["result"]["isError"]


def test_unknown_tool_is_reported_as_error():
    _, resp = drive("top", [{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                             "params": {"name": "nope", "arguments": {}}}])
    assert resp[0]["result"]["isError"]


def test_spawn_runs_worker_and_folds_in_observations():
    st0 = EpisodeState(SPEC, HSTAR)
    col = probeable_clearing(st0)
    calls = {}

    def fake_runner(task, budget, world_env):
        calls["task"], calls["budget"] = task, budget
        return {"observations": [[col, 1]], "used": 1, "report": "saw one cell"}

    st, resp = drive("top", [{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                              "params": {"name": "spawn",
                                         "arguments": {"task": "scout col", "budget": 2}}}],
                     runner=fake_runner)
    payload = tool_payload(resp[0])
    assert calls == {"task": "scout col", "budget": 2}     # grant = min(2, remaining 3)
    assert payload["observations"] == [[col, 1]] and payload["used"] == 1
    assert payload["remaining"] == SPEC.budget - 1         # only `used` charged; carve-out returns
    assert st.log[0]["via"] == "worker"


def test_spawn_with_no_budget_left_grants_nothing():
    def runner(task, budget, world_env):  # must not be called
        raise AssertionError("runner called with zero grant")

    reqs = [{"jsonrpc": "2.0", "id": i, "method": "tools/call",
             "params": {"name": "probe", "arguments": {"index": c}}}
            for i, c in enumerate(  # drain the whole budget first
                [j for j, cc in enumerate(EpisodeState(SPEC, HSTAR).cells)
                 if cc[0] == "direct"][:SPEC.budget])]
    reqs.append({"jsonrpc": "2.0", "id": 99, "method": "tools/call",
                 "params": {"name": "spawn", "arguments": {"task": "x", "budget": 2}}})
    _, resp = drive("top", reqs, runner=runner)
    assert "no budget" in tool_payload(resp[-1])["error"]
