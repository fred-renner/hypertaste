"""Chapter-2 meta-agent-on-program loop: channel accounting, coverage scoring, the blank-slate
seed, the mock end-to-end iteration, and the airgap (the solver imports no world internals; the
report leaks no register values)."""

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


# ---- channel accounting (mirrors the stdio probe server) ----
def test_channel_charges_and_serves_public_map():
    world = rw.RegisterWorld(SPEC, seed=1)
    ch = world.open_channel()
    info = ch.world_map()
    assert info["M"] == SPEC.M and info["K"] == SPEC.K and info["budget"] == SPEC.budget
    assert len(info["cells"]) == SPEC.M
    # a valid probe returns the true color and costs one probe
    val = ch.probe(0)
    assert val == world.cells[0]
    assert ch.remaining() == SPEC.budget - 1
    # out-of-range (but in budget) still costs a probe and returns None
    assert ch.probe(10_000) is None
    assert ch.remaining() == SPEC.budget - 2
    # spend the rest, then an over-budget probe costs nothing and returns None
    while ch.remaining() > 0:
        ch.probe(1)
    before = len(ch.history())
    assert ch.probe(2) is None
    assert ch.remaining() == 0
    assert len(ch.history()) == before + 1  # recorded as malformed, no charge


def test_coverage_score_in_band():
    world = rw.RegisterWorld(SPEC, seed=2)
    # a perfect reconstruction tops the band; an empty one floors valid=False
    perfect = world.score(list(world.cells))
    assert perfect["raw"] == 1.0 and perfect["valid"] and perfect["norm"] == 1.0
    none = world.score(None)
    assert none["valid"] is False and 0.0 <= none["norm"] <= 1.0


# ---- the blank-slate seed runs and submits a full reconstruction ----
def test_seed_solver_reconstructs_full_length(tmp_path):
    cfg = _mock_cfg(tmp_path)
    solver = load_solver(ch2_loop.SEED_DIR)
    world = rw.RegisterWorld(SPEC, seed=3)
    rec = ch2_loop._run_on_world(solver, world, cfg)
    assert isinstance(rec["recon"], list) and len(rec["recon"]) == SPEC.M
    # it spent its probes through the channel (the mock llm gives no plan -> deterministic fill)
    used = [h for h in rec["history"] if not h.get("malformed")]
    assert 0 < len(used) <= SPEC.budget
    # observed cells are reconstructed exactly (the seed places what it probed)
    for h in used:
        assert rec["recon"][h["index"]] == h["value"]


# ---- airgap: the seed solver imports nothing from the world ----
def test_seed_solver_imports_no_world_internals():
    src = open(os.path.join(ch2_loop.SEED_DIR, "solver.py")).read()
    imports = [ln.strip() for ln in src.splitlines()
               if re.match(r"\s*(import|from)\s", ln)]
    for ln in imports:  # the solver may only import stdlib (it gets the world via channel/llm)
        for bad in ("hta", "world", "engine", "threshold", "register", ".."):
            assert bad not in ln, f"seed solver import crosses the airgap: {ln!r}"


# ---- airgap: the sanitized report leaks no hidden register values ----
def test_report_hides_register_values(tmp_path):
    cfg = _mock_cfg(tmp_path)
    solver = load_solver(ch2_loop.SEED_DIR)
    worlds = [rw.RegisterWorld(SPEC, seed=s) for s in (7, 8)]
    ev = ch2_loop.evaluate(ch2_loop.SEED_DIR, worlds, cfg)
    report = ev["report_md"]
    # the true register tuple must not appear verbatim anywhere in what the meta agent reads
    for w in worlds:
        assert str(list(w.regs)) not in report
        assert repr(tuple(w.regs)) not in report


# ---- mock end-to-end: one iteration seeds, branches, evaluates, archives ----
def test_iteration_end_to_end(tmp_path):
    cfg = _mock_cfg(tmp_path)
    rep = ch2_loop.run_iteration(cfg, SPEC, iteration=0)
    assert rep["parent"] == 0 and rep["child"] == 1
    assert rep["valid_child"] is True
    # the archive grew and the child node carries a coverage fitness + program size
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
    assert rep["child"] == 2  # lineage extends, archive keeps growing
    assert rep["valid_child"] is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
