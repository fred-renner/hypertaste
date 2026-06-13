"""Instance-0 machine-world tests — deterministic, pure compute, no API cost.

Verify the kit v1 deliverables (PLAN.md -> record v2, "The proof of principle"):
- the builder draws fresh-but-reproducible machines, and component composition collapses to the
  advertised observable law (const / affine / table);
- the dumb exam scorer obeys the contract: perfect = 1, all-abstain = 0 (the blind baseline), a
  committed wrong value scores below abstaining, abstain earns exactly the blind-guess credit;
- the public map leaks no hidden values (the generality sieve);
- the build-screen gate holds: scripted probers (random / sweep-and-fit / even-enumerate) all land
  ≈ 0 of the band, while a reference tasteful allocator clears them — a real taste gap exists;
- the episode substrate and the stdio-MCP framing are exercised offline (the airgap is testable
  without a live claude -p), and the mock player drives probe -> submit -> score.
"""

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.ch2.machine import (  # noqa: E402
    Blueprint, Output, blind_baseline, draw_machine, observable_kind, perfect_score, score_models,
)
from hta.ch2 import machine_qa as qa  # noqa: E402
from hta.ch2 import machine_loop as ml  # noqa: E402
from hta.ch2.machine_state import MachineEpisode, machine_from_env, machine_to_env  # noqa: E402
from hta.ch2.machine_server import serve  # noqa: E402


# ---- the builder + composition -------------------------------------------------
def test_draw_is_deterministic_and_fresh():
    bp = ml.instance0()
    a = draw_machine(bp, 42)
    b = draw_machine(bp, 42)
    c = draw_machine(bp, 43)
    assert a.to_dict() == b.to_dict()          # same seed -> same machine (replayable)
    assert a.to_dict() != c.to_dict()          # a different seed is a different machine
    # the public shape is identical across draws (only the hidden kind/params re-roll)
    assert [(o.domain, o.weight) for o in a.outputs] == [(o.domain, o.weight) for o in c.outputs]


def test_observable_kind_collapses():
    assert observable_kind([{"t": "affine", "a": 2, "b": 1}, {"t": "affine", "a": 1, "b": 3}]) == "affine"
    assert observable_kind([{"t": "lookup", "table": [0, 1]}, {"t": "affine", "a": 2, "b": 0}]) == "table"
    assert observable_kind([{"t": "const", "c": 4}, {"t": "affine", "a": 9, "b": 1}]) == "const"


def test_chain_composition_value():
    # input -> affine(a=2,b=1) -> affine(a=1,b=3):  ((2x+1)*1+3) = 2x+4
    o = Output(domain=5, weight=2, chain=({"t": "affine", "a": 2, "b": 1}, {"t": "affine", "a": 1, "b": 3}))
    assert [o.f(x) for x in range(5)] == [2 * x + 4 for x in range(5)]
    assert o.kind() == "affine"


# ---- the scorer contract -------------------------------------------------------
def _affine_machine():
    """A tiny machine of known laws so the scorer math is checkable by hand."""
    outs = (
        Output(domain=4, weight=1, chain=({"t": "affine", "a": 2, "b": 1},)),   # 1,3,5,7
        Output(domain=3, weight=2, chain=({"t": "const", "c": 5},)),            # 5,5,5
        Output(domain=4, weight=1, chain=({"t": "lookup", "table": [3, 1, 4, 1]},)),  # 3,1,4,1
    )
    from hta.ch2.machine import Machine
    return Machine(name="hand", outputs=outs, budget=6)


def test_perfect_is_one_and_abstain_is_zero():
    m = _affine_machine()
    perfect = {0: {"law": "affine", "a": 2, "b": 1},
               1: {"law": "const", "c": 5},
               2: {"law": "table", "values": {"0": 3, "1": 1, "2": 4, "3": 1}}}
    s = score_models(m, perfect)
    assert s["norm"] == 1.0 and s["raw"] == s["perfect"]

    # all-abstain == the blind baseline == norm 0
    s0 = score_models(m, {})
    assert abs(s0["raw"] - blind_baseline(m)) < 1e-9
    assert s0["norm"] == 0.0


def test_wrong_commit_scores_below_abstain():
    m = _affine_machine()
    # commit a wrong line on the table output (output 2) -> earns ~0 there, below abstaining
    wrong = {2: {"law": "affine", "a": 7, "b": 7}}
    s_wrong = score_models(m, wrong)
    s_abstain = score_models(m, {})
    assert s_wrong["norm"] < s_abstain["norm"]            # confident wrong < honest abstain
    assert s_wrong["norm"] < 0                            # below the blind baseline


def test_abstain_credit_equals_blind_per_question():
    m = _affine_machine()
    # answering one output with its best lazy constant equals abstaining on it
    # output 1 is constant 5 -> the lazy constant wins it fully; abstaining earns the same
    s_const = score_models(m, {1: {"law": "const", "c": 5}})
    s_abstain1 = score_models(m, {1: {"law": "abstain"}})
    # output 1 fully won by const; abstain earns its full blind credit (modal value = 5 everywhere)
    po_const = next(p for p in s_const["per_output"] if p["output"] == 1)
    po_abs = next(p for p in s_abstain1["per_output"] if p["output"] == 1)
    assert po_const["earned"] == po_abs["earned"] == po_const["perfect"]


def test_partial_table_beats_abstain_but_not_full():
    m = _affine_machine()
    partial = {2: {"law": "table", "values": {"0": 3, "2": 4}}}   # 2 of 4 right, abstain rest
    s = score_models(m, partial)
    po = next(p for p in s["per_output"] if p["output"] == 2)
    assert po["correct"] == 2 and po["wrong"] == 0
    assert po["earned"] > po["blind"]                    # the two known cells beat blind
    assert po["earned"] < po["perfect"]


# ---- the generality sieve: no hidden values on any agent surface ----------------
def test_public_map_leaks_no_hidden_values():
    bp = ml.instance0()
    a, b = draw_machine(bp, 7), draw_machine(bp, 8)
    # different hidden machines, identical public face -> the map carries no hidden information
    assert a.to_dict() != b.to_dict()
    assert a.public_map(a.budget) == b.public_map(b.budget)
    pm = a.public_map(a.budget)
    assert set(pm["outputs"][0]) == {"output", "domain", "weight"}   # nothing else exposed per output
    assert pm["n_outputs"] == len(a.outputs)


# ---- the build-screen gate (PLAN.md §3 gate 1) ----------------------------------
def test_screen_gate_holds():
    r = qa.screen_blueprint(ml.instance0(), seeds=range(60))
    for name in ("random_poke", "sweep_fit", "enumerate_even"):
        assert r[name] <= 0.25, f"{name} too high ({r[name]}) — world is too easy"
    assert r["reference_tasteful"] > r["scripted_floor"] + 0.08, "no taste gap above the scripted floor"


def test_scripted_probers_respect_budget():
    m = draw_machine(ml.instance0(), 11)
    for fn in (qa.random_poke, qa.sweep_fit, qa.enumerate_even, qa.reference_tasteful):
        s = fn(m, seed=3)
        assert -1.0 <= s["norm"] <= 1.0


# ---- the episode substrate -----------------------------------------------------
def test_episode_budget_and_validation():
    m = draw_machine(ml.instance0(), 5)
    ep = MachineEpisode(m)
    assert ep.probe(0, 0)["value"] == m.outputs[0].f(0)
    assert ep.remaining_budget() == m.budget - 1
    assert ep.probe(99, 0)["value"] is None        # out-of-range output rejected, not charged
    assert ep.probe(0, 9999)["value"] is None      # out-of-range input rejected
    assert ep.remaining_budget() == m.budget - 1
    # spend the whole budget, then a probe is refused
    while ep.remaining_budget() > 0:
        ep.probe(0, ep.remaining_budget() % m.outputs[0].domain)
    assert ep.probe(1, 0)["error"] == "out of budget"
    ep.submit({0: {"law": "abstain"}})
    assert ep.done and isinstance(ep.score()["norm"], float)


def test_env_roundtrip():
    m = draw_machine(ml.instance0(), 9)
    ep = machine_from_env(machine_to_env(m))
    assert ep.machine.to_dict() == m.to_dict()


# ---- the stdio-MCP framing (the airgap, exercised offline) ----------------------
def _rpc(*msgs):
    return io.StringIO("\n".join(json.dumps(mm) for mm in msgs) + "\n")


def test_server_framing_probe_and_submit():
    m = draw_machine(ml.instance0(), 13)
    ep = MachineEpisode(m)
    out = io.StringIO()
    serve(ep, _rpc(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "machine_map", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "probe", "arguments": {"output": 0, "input": 0}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "submit", "arguments": {"models": {"0": {"law": "abstain"}}}}},
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
         "params": {"name": "nope", "arguments": {}}},
    ), out)
    lines = [json.loads(l) for l in out.getvalue().splitlines() if l.strip()]
    by_id = {m_["id"]: m_ for m_ in lines}
    tools = {t["name"] for t in by_id[2]["result"]["tools"]}
    assert {"probe", "submit", "machine_map", "remaining", "mem_read", "mem_patch"} == tools
    probe_payload = json.loads(by_id[4]["result"]["content"][0]["text"])
    assert probe_payload["value"] == m.outputs[0].f(0)
    submit_payload = json.loads(by_id[5]["result"]["content"][0]["text"])
    assert submit_payload["accepted"] is True
    assert by_id[6]["result"]["isError"] is True   # unauthorized tool refused
    assert ep.done


# ---- the mock player + the inner-loop plumbing ----------------------------------
def test_mock_player_and_inner_loop_plumbing():
    m = draw_machine(ml.instance0(), 17)
    res = ml._mock_player(m)
    assert res["submitted"] and res["used"] <= m.budget
    s = score_models(m, res["submitted"])
    assert s["norm"] > 0.0                          # the fixed mock policy beats lazy

    from hta.config import Config
    cfg = Config()
    cfg.backend = "mock"
    out = ml.run_instance0(cfg, n_train=2, n_holdout=2, coaching_rounds=1, seed=1, log=lambda *a, **k: None)
    assert set(out) >= {"bare_norm", "day_one_norm", "coached_norm", "gap_coached_minus_dayone"}
    assert out["day_one_playbook"] and out["coached_playbook"]
