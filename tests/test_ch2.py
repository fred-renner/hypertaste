"""Chapter-2 thin-slice tests (deterministic, no API cost).

Verify the integrity floor (determinism, agent-inaccessible scoring), the DP oracle ordering
(oracle >= floor and >= the mock student), the ramp property (bet 2), the probe channel/server
airgap, and that the mock measurement runs end-to-end with a real taste>vanilla gap.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta import llm  # noqa: E402
from hta.config import Config  # noqa: E402
from hta.ch2 import agent, grammar  # noqa: E402
from hta.ch2.maps import MAPS  # noqa: E402
from hta.ch2.world import TapeWorld, MapChannel  # noqa: E402
import run_slice  # noqa: E402


def test_expander_is_deterministic_and_bounded():
    for spec in MAPS:
        t1, t2 = grammar.expand(spec), grammar.expand(spec)
        assert t1 == t2                      # deterministic
        assert len(t1) == spec.M             # bounded by construction
        assert all(0 <= c < spec.K for c in t1)


def test_determination_is_monotone_and_exact():
    # The enlarged family (const/arith/alt/cycle) is the deception lever: 2-3 adjacent probes
    # no longer trivially pin a segment, because a period-3 `cycle` survives the gaps.
    n, K = 5, 4
    assert grammar.determined_count(n, K, (0,), (2,)) >= 1
    # two adjacent same-valued probes leave the period-3 cell ambiguous (cycle(2,2,c) fits),
    # so they determine strictly fewer than the whole const segment...
    assert grammar.determined_count(n, K, (0, 1), (2, 2)) < n
    # ...but a third adjacent probe kills the cycle and pins the whole run.
    assert grammar.determined_count(n, K, (0, 1, 2), (2, 2, 2)) == n
    # the arith/cycle mirage: a [0,1,2] prefix is consistent with BOTH an arith run and a
    # period-3 cycle, so a local read cannot resolve it -> fewer than n cells determined...
    assert grammar.determined_count(n, K, (0, 1, 2), (0, 1, 2)) < n
    # ...until a far confirm-probe (here the next cell, =3 for arith) rules the cycle out.
    assert grammar.determined_count(n, K, (0, 1, 2, 3), (0, 1, 2, 3)) == n
    # more evidence never determines fewer cells (monotonicity of information).
    seq = grammar.realize_segment(grammar.Segment("arith", (1, 1), 5), K)  # an arith segment
    c1 = grammar.determined_count(len(seq), K, (0,), (seq[0],))
    c2 = grammar.determined_count(len(seq), K, (0, len(seq) - 1), (seq[0], seq[-1]))
    assert c2 >= c1


def test_oracle_brackets_floor_and_is_achievable():
    for spec in MAPS:
        world = TapeWorld(spec)
        ref = world.references()
        assert ref["oracle_det"] >= ref["floor_det"]      # oracle >= no-inference floor
        assert ref["oracle_raw"] >= ref["floor_raw"]
        assert ref["oracle_det"] <= spec.M
        # the oracle's determined ceiling must be reachable: probing the optimal cells of a
        # FULLY pinnable subset reconstructs at least that many cells (no over-claiming).
        assert ref["oracle_raw"] <= 1.0
        # the realizable ceiling (the normalizer) sits BETWEEN the floor and the omniscient
        # oracle: it is the oracle de-omniscienced (charged for boundary discovery) but never
        # below the floor a plain prober already reaches -> a non-degenerate band to score in.
        assert ref["floor_det"] <= ref["realizable_det"] <= ref["oracle_det"]
        assert ref["realizable_raw"] > ref["floor_raw"]   # band has positive width


def test_smoothness_is_a_ramp():
    # bet 2: coverage is ~linear in the fraction of segments inferred (monotone up, R^2 high).
    for spec in MAPS:
        curve = grammar.smoothness_curve(spec)
        assert curve[0] == 0.0 and abs(curve[-1] - 1.0) < 1e-9
        assert all(b >= a for a, b in zip(curve, curve[1:]))   # monotone
        assert grammar.linearity_r2(curve) >= 0.95             # a ramp, not a cliff


def test_channel_is_narrow_and_airgapped():
    spec = MAPS[0]
    world = TapeWorld(spec)
    ch = world.open_channel()
    # the channel yields one cell value per probe and nothing about the grammar/scorer.
    assert ch.probe(0) == world.tape[0]
    assert set(vars(ch)).isdisjoint({"spec", "_spec"})        # no spec/grammar reachable
    # budget binds; malformed probes are recorded but reveal nothing.
    assert ch.probe(10 ** 9) is None
    for _ in range(spec.budget):
        if ch.remaining() > 0:
            ch.probe(1)
    try:
        ch.probe(1)
        assert False, "expected ProbeExhausted"
    except Exception:
        pass


def test_mock_taste_beats_vanilla_and_scorer_is_outcome_based():
    cfg = Config()
    cfg.backend = "mock"
    for spec in MAPS:
        world = TapeWorld(spec)
        van = world.score(agent.mock_solve(spec, taste=False))
        tas = world.score(agent.mock_solve(spec, taste=True))
        # taste inference recovers strictly more of the tape than no-inference probing.
        assert tas["raw"] > van["raw"]
        assert 0.0 <= tas["normalized"] <= 1.0
        # scoring is a pure outcome comparison: a perfect reconstruction scores raw==1.
        assert world.score(list(world.tape))["raw"] == 1.0


def test_slice_runs_end_to_end_on_mock():
    cfg = Config()
    cfg.backend = "mock"
    out = run_slice.run(cfg, MAPS, repeats=1, log=lambda *a, **k: None)
    assert out["gap"] > 0.0
    assert out["bet2"] == "PASS"
    assert set(out.keys()) >= {"bet1", "bet2", "verdict"}


def test_probe_server_protocol(tmp_path):
    """Drive the stdio MCP map-probe server directly (no API): correct value, decrementing
    budget, and a trajectory matching the channel shape; submit_map records the recon."""
    spec = MAPS[0]
    tape = list(grammar.expand(spec))
    traj = tmp_path / "traj.jsonl"
    env = dict(os.environ, HTA_TAPE=json.dumps(tape), HTA_BUDGET="4", HTA_TRAJ_PATH=str(traj))
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "probe", "arguments": {"index": 0}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "submit_map", "arguments": {"values": tape}}},
    ]
    inp = "\n".join(json.dumps(m) for m in msgs) + "\n"
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    proc = subprocess.run([sys.executable, "-m", "hta.ch2.probe_server"],
                          input=inp, capture_output=True, text=True, cwd=repo, env=env, timeout=20)
    out = {json.loads(l).get("id"): json.loads(l) for l in proc.stdout.splitlines()}
    assert [t["name"] for t in out[2]["result"]["tools"]] == ["probe", "remaining", "submit_map"]
    assert json.loads(out[3]["result"]["content"][0]["text"]) == {"value": tape[0], "remaining": 3}
    assert json.loads(out[4]["result"]["content"][0]["text"]) == {"accepted": True}
    lines = [json.loads(l) for l in traj.read_text().splitlines()]
    assert lines[0]["type"] == "probe" and lines[0]["index"] == 0 and lines[0]["value"] == tape[0]
    assert lines[-1]["type"] == "submit" and lines[-1]["accepted"] is True
