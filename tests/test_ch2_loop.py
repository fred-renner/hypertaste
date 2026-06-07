"""Chapter-2 meta-agent-on-program loop: the harness substrate (AgentContext + run_agent budget
accounting), coverage scoring, the blank-slate seed harness, the mock end-to-end iteration, and
the airgap (the harness imports no world internals; the report leaks no register values)."""

import os
import re

import pytest

from hta.config import Config
from hta.ch2 import loop as ch2_loop
from hta.ch2 import register_world as rw
from hta.ch2.threshold import LinkSpec
from hta.task_agent import load_solver

SPEC = LinkSpec("trap-tetra", R=5, K=3, Ld=2, Ll=2,
                edges=((1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)), budget=4, direct=(0,))


def _mock_cfg(tmp_path) -> Config:
    cfg = Config()
    cfg.backend = "mock"
    cfg.out_dir = str(tmp_path)
    cfg.n_train_worlds = 2
    cfg.n_transfer_worlds = 1
    return cfg


# ---- AgentContext: public map + a global budget shared across deployed agents ----
def test_context_public_map_and_shared_budget():
    world = rw.RegisterWorld(SPEC, seed=1)
    ctx = rw.AgentContext(world, _mock_cfg_inline())
    info = ctx.world_map()
    assert info["M"] == SPEC.M and info["K"] == SPEC.K and info["budget"] == SPEC.budget
    assert len(info["cells"]) == SPEC.M
    assert ctx.remaining() == SPEC.budget
    # deploy two mock agents with 2 probes each: budget is shared, observations accumulate
    r1 = ctx.run_agent("p", max_probes=2)
    assert r1["probes_used"] == 2 and ctx.remaining() == SPEC.budget - 2
    r2 = ctx.run_agent("p", max_probes=2)
    assert r2["probes_used"] == 2 and ctx.remaining() == 0
    assert len(ctx.observations()) == 4  # 4 distinct cells probed across the two agents
    # over-budget deploy spends nothing
    r3 = ctx.run_agent("p", max_probes=2)
    assert r3["probes_used"] == 0 and ctx.remaining() == 0
    # observed cells carry their true colors
    for idx, val in ctx.observations().items():
        assert val == world.cells[idx]


def _mock_cfg_inline() -> Config:
    cfg = Config()
    cfg.backend = "mock"
    return cfg


def test_coverage_score_in_band():
    world = rw.RegisterWorld(SPEC, seed=2)
    perfect = world.score(list(world.cells))
    assert perfect["raw"] == 1.0 and perfect["valid"] and perfect["norm"] == 1.0
    none = world.score(None)
    assert none["valid"] is False and 0.0 <= none["norm"] <= 1.0


# ---- the blank-slate seed harness runs and returns a full reconstruction ----
def test_seed_harness_reconstructs_full_length(tmp_path):
    cfg = _mock_cfg(tmp_path)
    solver = load_solver(ch2_loop.SEED_DIR)
    world = rw.RegisterWorld(SPEC, seed=3)
    rec = ch2_loop._run_on_world(solver, world, cfg)
    assert isinstance(rec["recon"], list) and len(rec["recon"]) == SPEC.M
    # the seed deploys exactly one agent that spends the whole budget
    assert len(rec["agent_calls"]) == 1
    assert rec["agent_calls"][0]["probes_used"] == SPEC.budget
    # observed cells are reconstructed exactly (assembled from observations on the mock path)
    for idx, val in rec["observations"].items():
        assert rec["recon"][idx] == val


# ---- airgap: the seed harness imports nothing from the world ----
def test_seed_harness_imports_no_world_internals():
    src = open(os.path.join(ch2_loop.SEED_DIR, "solver.py")).read()
    imports = [ln.strip() for ln in src.splitlines()
               if re.match(r"\s*(import|from)\s", ln)]
    for ln in imports:  # the harness may only import stdlib; it gets the world via ctx
        for bad in ("hta", "world", "engine", "threshold", "register", ".."):
            assert bad not in ln, f"seed harness import crosses the airgap: {ln!r}"


# ---- airgap: the sanitized report leaks no hidden register values ----
def test_report_hides_register_values(tmp_path):
    cfg = _mock_cfg(tmp_path)
    worlds = [rw.RegisterWorld(SPEC, seed=s) for s in (7, 8)]
    ev = ch2_loop.evaluate(ch2_loop.SEED_DIR, worlds, cfg)
    report = ev["report_md"]
    for w in worlds:
        assert str(list(w.regs)) not in report
        assert repr(tuple(w.regs)) not in report


# ---- mock end-to-end: one iteration seeds, branches, evaluates, archives ----
def test_iteration_end_to_end(tmp_path):
    cfg = _mock_cfg(tmp_path)
    rep = ch2_loop.run_iteration(cfg, SPEC, iteration=0)
    assert rep["parent"] == 0 and rep["child"] == 1
    assert rep["valid_child"] is True
    archive_dir = cfg.archive_dir
    assert os.path.isdir(os.path.join(archive_dir, "gen_0000"))
    assert os.path.isdir(os.path.join(archive_dir, "gen_0001"))
    child_meta = open(os.path.join(archive_dir, "gen_0001", "node.json")).read()
    assert '"spec": "trap-tetra"' in child_meta
    assert '"program_size"' in child_meta
    # the mock meta edit flipped the seed's plumbing fixture (observable behavior change)
    child_solver = open(os.path.join(archive_dir, "gen_0001", "solver.py")).read()
    assert '_MOCK_VARIANT = "edited"' in child_solver


def test_second_iteration_compounds(tmp_path):
    cfg = _mock_cfg(tmp_path)
    ch2_loop.run_iteration(cfg, SPEC, iteration=0)
    rep = ch2_loop.run_iteration(cfg, SPEC, iteration=1)
    assert rep["child"] == 2
    assert rep["valid_child"] is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
