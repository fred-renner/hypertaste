"""DGM-H loop tests (hta/dgmh/loop.py) — the world-agnostic iteration loop, mock backend.
Deterministic, offline, no API cost.

The load-bearing claims:
- One mock iteration runs end to end on instance 0: seed gen_0000, eval parent, branch a child, eval
  child, archive — and persists an auditable iter record.
- The score is a pure replay: `score_result(spec, hstar, result)` reproduces a score from the log +
  submission with no live process.
- The sanitized meta report carries the agent's CONDUCT + the PUBLIC structure, never a hidden seed
  or an un-probed cell's true value.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.config import Config  # noqa: E402
from hta.dgmh import loop  # noqa: E402
from hta.world.instances import draw_hstar, instance0  # noqa: E402


def _cfg(tmp_path):
    cfg = Config()
    cfg.backend = "mock"
    cfg.out_dir = str(tmp_path)
    cfg.n_train_worlds = 2
    cfg.n_transfer_worlds = 1
    return cfg


def test_one_mock_iteration_end_to_end(tmp_path):
    cfg = _cfg(tmp_path)
    rep = loop.run_iteration(cfg, iteration=0)
    assert rep["parent"] == 0 and rep["child"] == 1 and rep["valid_child"]
    # the archive has both nodes; the child branched from the seed
    from hta.dgmh.archive import Archive
    arc = Archive(cfg.archive_dir)
    assert arc.genids() == [0, 1]
    assert os.path.exists(os.path.join(cfg.out_dir, "iter_0000.json"))


def test_score_result_is_a_pure_replay():
    spec = instance0()
    hstar = draw_hstar(spec, 11)
    result = loop._mock_floor_player(spec, hstar)
    sc, st = loop.score_result(spec, hstar, result)
    # replaying the SAME log + submission reproduces the same score (no live process involved)
    sc2, _ = loop.score_result(spec, hstar, result)
    assert sc == sc2 and sc["raw"] == sc["floor"]


def test_sanitized_report_hides_the_seed():
    spec = instance0()
    hstar = draw_hstar(spec, 12)
    rec = loop.run_episode("", spec, hstar, _cfg_inline())
    floor, oracle = sc_band(spec)
    md = loop._sanitized_report([rec], spec, floor, oracle)
    assert "conduct" in md.lower() and "floor" in md.lower()
    # the raw hidden seed tuple must not appear verbatim in the report
    assert str(list(hstar)) not in md


def _cfg_inline():
    cfg = Config()
    cfg.backend = "mock"
    return cfg


def sc_band(spec):
    from hta.world import grade
    return grade.floor_value(spec), grade.oracle_value(spec)
