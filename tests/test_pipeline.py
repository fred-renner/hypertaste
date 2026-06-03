"""Pipeline smoke tests on the deterministic mock backend (no API cost).

These verify the machinery end-to-end: the loop runs, the child is a valid program,
the mock improvement raises fitness, the archive grows, and the report handed to the
meta agent does not leak hidden-rule sources (airgap sanity).
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta import llm, loop, task_agent  # noqa: E402
from hta.archive import Archive  # noqa: E402
from hta.config import Config  # noqa: E402
from hta.world import world_smith, grammar  # noqa: E402


def _cfg(tmp):
    cfg = Config.testing()
    cfg.backend = "mock"
    cfg.out_dir = tmp
    return cfg


def test_iteration_improves(tmp_path):
    cfg = _cfg(str(tmp_path))
    llm.reset_accounting()
    rep = loop.run_iteration(cfg)
    assert rep["valid_child"] is True
    # mock flips naive->smart, which must not regress and should improve.
    assert rep["child_fitness"] >= rep["parent_fitness"]
    assert rep["improved"] is True
    # archive grew beyond the seed.
    arch = Archive(cfg.archive_dir)
    assert len(arch.genids()) >= 2


def test_smart_solver_recovers_classic_rule(tmp_path):
    """The 'smart' mock strategy should exactly recover x<y<z by falsification +
    Occam induction, using only observed booleans."""
    cfg = _cfg(str(tmp_path))
    # build the classic world directly
    rule = next(r for r in grammar.candidate_library() if r.name == "strict_increasing")
    from hta.world.engine import WiltWorld
    world = WiltWorld(rule, max_probes=cfg.max_probes)
    # write a smart solver to a temp dir
    seed_dir = loop.SEED_DIR
    work = tmp_path / "smart"
    shutil.copytree(seed_dir, work)
    src = (work / "solver.py").read_text().replace('STRATEGY = "naive"', 'STRATEGY = "smart"')
    (work / "solver.py").write_text(src)
    solver = task_agent.load_solver(str(work))
    rec = task_agent.run_on_world(solver, world, cfg)
    assert rec["metrics"]["solved"] is True


def test_report_does_not_leak_rule(tmp_path):
    cfg = _cfg(str(tmp_path))
    worlds = world_smith.transfer_suite(cfg)
    agg = task_agent.evaluate(loop.SEED_DIR, worlds, cfg)
    report = agg["report_md"]
    # the sanitized report must not contain any hidden rule's name or source
    for w in worlds:
        assert w.rule.name not in report
        assert w.rule.source not in report


def test_unsafe_guess_rejected():
    from hta.world.grammar import validate_lambda
    assert validate_lambda("lambda x, y, z: x < y < z") is True
    assert validate_lambda("lambda x, y, z: __import__('os').system('id')") is False
    assert validate_lambda("lambda x, y, z: open('/etc/passwd')") is False


def test_probe_server_protocol(tmp_path):
    """Drive the stdio MCP probe server directly (no API): correct booleans, a
    decrementing budget, and a trajectory log matching channel.history() shape."""
    import json
    import subprocess

    traj = tmp_path / "traj.jsonl"
    env = dict(os.environ, HTA_RULE_SRC="lambda x, y, z: x < y < z",
               HTA_MAX_PROBES="5", HTA_TRAJ_PATH=str(traj))
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "probe", "arguments": {"x": 1, "y": 2, "z": 3}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "probe", "arguments": {"x": 3, "y": 2, "z": 1}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "submit_guess", "arguments": {"rule": "lambda x, y, z: x < y < z"}}},
    ]
    inp = "\n".join(json.dumps(m) for m in msgs) + "\n"
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    proc = subprocess.run([sys.executable, "-m", "hta.world.probe_server"],
                          input=inp, capture_output=True, text=True, cwd=repo, env=env, timeout=20)
    out = {json.loads(l).get("id"): json.loads(l) for l in proc.stdout.splitlines()}
    assert [t["name"] for t in out[2]["result"]["tools"]] == ["probe", "remaining", "submit_guess"]
    assert json.loads(out[3]["result"]["content"][0]["text"]) == {"result": True, "remaining": 4}
    assert json.loads(out[4]["result"]["content"][0]["text"]) == {"result": False, "remaining": 3}
    lines = [json.loads(l) for l in traj.read_text().splitlines()]
    assert lines[0]["type"] == "probe" and lines[0]["triple"] == [1, 2, 3] and lines[0]["label"] is True
    assert lines[-1]["type"] == "guess" and lines[-1]["accepted"] is True


def test_curriculum_escalates(tmp_path):
    """ZPD: as the best agent keeps solving, the world-smith's target difficulty must
    climb above its starting point, and weak tags are computed + persisted."""
    from hta.archive import Archive

    cfg = _cfg(str(tmp_path))
    for i in range(3):
        loop.run_iteration(cfg, seed=i)
    arch = Archive(cfg.archive_dir)
    diffs = [arch._meta(g).get("target_difficulty") for g in arch.genids()
             if arch._meta(g).get("target_difficulty") is not None]
    assert max(diffs) > min(diffs)  # difficulty escalated
    assert max(diffs) >= 3
    # weak_tags key is persisted on evaluated children
    assert all("weak_tags" in arch._meta(g) for g in arch.genids() if arch._meta(g).get("fitness") is not None)
