"""Tests for the situation harness (hta/ch2/situations.py) and the trajectory renderer
(hta/ch2/trajectory.py): a constructed mid-episode state materializes deterministically (prefix
charged, belief refined, scratchpad seeded), rides the env airgap to a probe server, and is
scored against its own best-play-continuation band; the renderer shows only what the player
observed. Plus the loop wiring for the hidden-map world (mock, offline, free)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.config import Config  # noqa: E402
from hta.ch2 import situations, trajectory  # noqa: E402
from hta.ch2.episode_state import draw_hstar, state_from_env  # noqa: E402
from hta.ch2.situations import Situation  # noqa: E402
from tests.test_hidden_map import tiny_spec  # noqa: E402


def _sit(remaining=2):
    spec = tiny_spec()
    hstar = draw_hstar(spec, seed=7)
    cells = spec.cells()
    backbone = next(i for i, c in enumerate(cells) if c[0] == "backbone")
    key0 = next(i for i, c in enumerate(cells) if c[0] == "key" and c[1] == 0)
    return Situation(name="drill", spec=spec, hstar=hstar, probed=(backbone, key0),
                     mem="backbone and g0 key pinned; g0 depth unknown", remaining=remaining)


def test_materialize_replays_prefix_and_seeds_scratchpad():
    sit = _sit(remaining=2)
    st = situations.materialize(sit)
    assert st.used == 2 and st.remaining_cost() == 2       # prefix charged; remaining honored
    assert [e["col"] for e in st.log] == list(sit.probed)
    assert st.mem == sit.mem
    assert len(st.observed_belief()) < len(st.table)       # the belief actually refined


def test_situation_rides_the_env_airgap():
    sit = _sit(remaining=1)
    st = state_from_env(situations.to_env(sit))
    assert [e["col"] for e in st.log] == list(sit.probed)
    assert st.mem == sit.mem and st.remaining_cost() == 1


def test_mock_run_scores_in_the_situation_band():
    cfg = Config()
    cfg.backend = "mock"
    sit = _sit(remaining=3)
    rec = situations.run_situation("(playbook unused in mock)", sit, cfg)
    s = rec["score"]
    assert s["floor"] == 0.0                               # key+backbone alone pin no region
    assert s["ceiling"] > 0
    assert 0.0 <= s["norm"] <= 1.0
    assert s["raw"] >= 0 and s["situation"] == "drill"


def test_do_nothing_continuation_scores_zero():
    sit = _sit(remaining=2)
    st = situations.materialize(sit)
    st.submit_map({})                                      # resume and immediately give up
    s = situations.score_situation(sit, st.result())
    assert s["raw"] == 0 and s["norm"] == 0.0


def test_situation_serialization_round_trip():
    sit = _sit()
    again = Situation.from_dict(sit.to_dict())
    assert again == sit


def test_trajectory_renders_only_observed_state():
    cfg = Config()
    cfg.backend = "mock"
    sit = _sit(remaining=3)
    rec = situations.run_situation("", sit, cfg)
    md = trajectory.render(sit.spec, rec["result"], score=rec["score"])
    assert "# Trajectory — tiny" in md and "Discovered map" in md
    assert "backbone" in md and "Submission" in md
    # the sketch shows only probed structure: the un-probed bait key may stay "?"
    hidden = sit.hstar
    assert str(list(hidden)) not in md


def test_loop_runs_mock_iteration_on_a_hidden_world(tmp_path):
    from hta.ch2 import loop as ch2_loop
    spec = tiny_spec()
    train, transfer = ch2_loop.build_worlds(2, 1, iteration=0, spec=spec)
    assert all(s.name == "tiny" for s, _ in train + transfer)
    shapes = {s_h[1] for s_h in train + transfer}
    assert len(shapes) == 3                                # fresh topologies by construction
    rec = ch2_loop.run_episode("", spec, train[0][1], Config())
    s = rec["score"]
    assert s["floor"] == 0.0                               # the band is 0 -> best-play here
    assert 0.0 <= s["norm"] <= 1.0


def test_world_kind_selects_the_hidden_canonical():
    from hta.ch2 import loop as ch2_loop
    cfg = Config()
    cfg.world_kind = "hidden"
    assert ch2_loop.world_spec(cfg).name == "hidden-map"
    cfg.world_kind = "anchor"
    assert ch2_loop.world_spec(cfg).name == "anchor"
