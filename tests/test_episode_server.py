"""Probe-MCP server tests (hta/dgmh/episode/server.py) — the airgap framing, exercised offline with
injected streams + an injected worker runner (no live claude -p). Deterministic, no API cost.

The load-bearing claims:
- The JSON-RPC framing answers initialize / tools/list / tools/call, one object per line.
- The role airgap holds: a `worker` session is offered ONLY probe/remaining; world_map/submit/spawn
  are unauthorized and rejected even if requested.
- A spawn launches the injected worker against an isolated sub-budget and folds its observations back.
- Every mutating call flushes the episode result to the dropbox (so the parent can read it).
"""

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.dgmh.episode import server  # noqa: E402
from hta.dgmh.episode.state import EpisodeState  # noqa: E402
from hta.world.instances import draw_hstar, instance0  # noqa: E402


def _spec():
    return instance0()


def _rpc(*msgs):
    return "".join(json.dumps(m) + "\n" for m in msgs)


def _run(role, msgs, runner=None, result_path=None):
    spec = _spec()
    st = EpisodeState(spec, draw_hstar(spec, 7))
    out = io.StringIO()
    kwargs = {}
    if runner is not None:
        kwargs["runner"] = runner
    server.serve(st, role, io.StringIO(_rpc(*msgs)), out, result_path=result_path, **kwargs)
    replies = [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]
    return st, replies


def _content(reply):
    return json.loads(reply["result"]["content"][0]["text"])


def test_initialize_and_tools_list_roles():
    _, replies = _run("top", [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])
    assert replies[0]["result"]["serverInfo"]["name"] == "probe"
    top_tools = {t["name"] for t in replies[1]["result"]["tools"]}
    assert {"probe", "spawn", "submit_map", "world_map", "mem_patch"} <= top_tools
    _, wreplies = _run("worker", [{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}])
    worker_tools = {t["name"] for t in wreplies[0]["result"]["tools"]}
    assert worker_tools == {"probe", "remaining"}                # the role airgap


def test_worker_cannot_call_top_only_tools():
    _, replies = _run("worker", [
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "world_map", "arguments": {}}}])
    assert replies[0]["result"]["isError"]
    assert "unauthorized" in _content(replies[0])["error"]


def test_probe_then_submit_flushes_result(tmp_path):
    rp = str(tmp_path / "result.json")
    spec = _spec()
    direct_col = next(i for i, c in enumerate(spec.cells()) if c[0] == "direct")
    st, replies = _run("top", [
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "probe", "arguments": {"index": direct_col}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "submit_map", "arguments": {"values": {str(direct_col): 0}}}}],
        result_path=rp)
    assert _content(replies[0])["value"] is not None
    assert _content(replies[1])["accepted"]
    with open(rp) as f:
        dropped = json.load(f)
    assert dropped["used"] == 1 and dropped["submitted"] == {str(direct_col): 0} and dropped["done"]


def test_spawn_runs_injected_worker_and_folds_observations():
    def fake_runner(task, budget, world_env, log_path=None):
        return {"observations": [[0, 1]], "used": 1, "report": f"did {task!r} on {budget}"}

    st, replies = _run("top", [
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "spawn", "arguments": {"task": "scout the gate", "budget": 2}}}],
        runner=fake_runner)
    payload = _content(replies[0])
    assert payload["used"] == 1 and payload["observations"] == [[0, 1]]
    assert any(e["via"] == "worker" for e in st.log)            # folded into the top's log
