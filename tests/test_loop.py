"""Tests for the Chapter-2 model-orchestrated loop (hta/_trail/loop.py) on the MOCK backend — the
offline plumbing path. The real path runs a live Haiku TOP session per episode (cents) + an Opus
playbook rewrite (~$1); none of that runs here. We prove: the iteration wiring (seed -> select ->
eval parent -> rewrite playbook -> eval child -> archive), the band judge replays a finished episode
deterministically, and the meta-agent report leaks no hidden world state.
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.config import Config  # noqa: E402
from hta._trail import anchor, loop as ch2_loop  # noqa: E402
from hta._trail.episode_state import EpisodeState, canonical_spec  # noqa: E402


def _mock_cfg(tmp):
    cfg = Config()
    cfg.backend = "mock"
    cfg.out_dir = tmp
    cfg.n_train_worlds = 2
    cfg.n_transfer_worlds = 1
    return cfg


def test_iteration_seeds_evaluates_and_archives():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _mock_cfg(tmp)
        rep = ch2_loop.run_iteration(cfg, iteration=0)
        assert rep["parent"] == 0 and rep["child"] == 1 and rep["valid_child"]
        # the mock floor-player scores at the floor of the band
        assert rep["child_norm"] == (0.0, 0.0)
        # the archive grew: seed + child, both with the English node and no solver.py
        from hta.dgmh.archive import Archive
        arc = Archive(cfg.archive_dir)
        assert arc.genids() == [0, 1]
        assert os.path.exists(os.path.join(arc.node_dir(1), "playbook.md"))
        assert not os.path.exists(os.path.join(arc.node_dir(1), "solver.py"))
        # the mock meta edit changed the child's playbook
        with open(os.path.join(arc.node_dir(1), "playbook.md")) as f:
            assert "plumbing-stub" in f.read()


def test_iteration_persists_replayable_artifacts():
    """PLAN.md Pass 0: each iteration writes an audit record (full transcripts + hidden draws)
    next to the archive, and a persisted transcript replays to its persisted score."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = _mock_cfg(tmp)
        ch2_loop.run_iteration(cfg, iteration=0)
        with open(os.path.join(tmp, "iter_0000.json")) as f:
            rec = json.load(f)
        assert len(rec["worlds"]["train"]) == 2 and len(rec["worlds"]["transfer"]) == 1
        per_world = rec["child_eval"]["train"]["per_world"]
        assert per_world and all("log" in r["result"] for r in per_world)
        spec = canonical_spec()
        hstar = tuple(rec["worlds"]["train"][0])
        score, _ = ch2_loop.score_result(spec, hstar, per_world[0]["result"])
        assert score["raw"] == per_world[0]["score"]["raw"]
        path = ch2_loop.persist_run(cfg, {"backend": "mock"}, [rec["summary"]],
                                    {"calls": 0, "cost_usd": 0.0})
        with open(path) as f:
            assert json.load(f)["history"][0]["child"] == 1


def test_seed_node_is_playbook_only():
    assert os.path.isfile(os.path.join(ch2_loop.SEED_DIR, "playbook.md"))
    with open(os.path.join(ch2_loop.SEED_DIR, "playbook.md")) as f:
        body = f.read()
    assert "probe" in body and "submit" in body
    assert "taste" not in body.lower()                     # the seed never names the target


def test_score_result_replays_a_trail_walk_to_the_oracle():
    spec = canonical_spec()
    hstar = ch2_loop.anchor_hstar(spec, 123)
    st = EpisodeState(spec, hstar)
    log = []
    for reg in spec.trail_regs(hstar):
        col = next(i for i, c in enumerate(st.cells) if c[0] == "sig" and c[1] == reg)
        log.append({"col": col, "value": anchor.cell_value(spec, st.cells[col], hstar),
                    "cost": 1, "via": "self"})
    valley = {i: anchor.cell_value(spec, c, hstar) for i, c in enumerate(st.cells) if c[0] == "valley"}
    result = {"log": log, "submitted": {str(k): v for k, v in valley.items()}, "used": 3, "spawns": []}
    score, _ = ch2_loop.score_result(spec, hstar, result)
    assert score["raw"] == anchor.oracle_value(spec)
    assert score["norm"] == 1.0


def test_report_is_sanitized_no_hidden_state_leak():
    spec = canonical_spec()
    hstar = ch2_loop.anchor_hstar(spec, 7)
    result = ch2_loop._mock_floor_player(spec, hstar)
    score, _ = ch2_loop.score_result(spec, hstar, result)
    report = ch2_loop._sanitized_report(
        [{"score": score, "result": result}], spec,
        anchor.floor_value(spec), anchor.oracle_value(spec))
    assert "sanitized" in report and "CONDUCT" in report
    # the hidden seed and the full reconstruction values are never dumped
    assert str(list(hstar)) not in report
    # every "col->value" shown corresponds to a cell the agent actually probed (not ground truth)
    probed = {e["col"] for e in result["log"]}
    for col in range(spec.M):
        if f"col{col}->" in report:
            assert col in probed


def test_build_worlds_train_and_transfer_are_disjoint_draws():
    train, transfer = ch2_loop.build_worlds(2, 2, iteration=0)
    assert len(train) == 2 and len(transfer) == 2
    seeds = {h for _, h in train} | {h for _, h in transfer}
    assert len(seeds) == 4                                  # four distinct hidden worlds
    assert all(spec.name == "anchor" for spec, _ in train + transfer)


def test_config_confines_top_and_worker_toolsets():
    cfg = Config()
    assert "mcp__probe__spawn" in cfg.top_allowed_tools
    assert "mcp__probe__submit_map" in cfg.top_allowed_tools
    assert set(cfg.worker_allowed_tools) == {"mcp__probe__probe", "mcp__probe__remaining"}
    assert "mcp__probe__spawn" not in cfg.worker_allowed_tools  # depth 1: workers cannot spawn
