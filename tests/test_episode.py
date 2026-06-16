"""Episode-state machine + band judge tests (hta/dgmh/episode/state.py). Deterministic, offline,
no API cost.

The load-bearing claims:
- The budget binds (a probe is charged its cost; an unaffordable/malformed probe is reported, not
  charged) and a valley is NOT probeable (inference-only).
- The judge is the dumb scorer: band-normalized coverage of the probe LOG + submission, capped to
  pinned cells. Walking the floor scores ~0 of the band; reconstructing the trail scores in-band.
- The spawn carve-out charges only what a worker spends and merges its observations into the log.
- The hidden seed round-trips through the env seam (the server-only channel).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.dgmh.episode.state import (EpisodeState, state_from_env, state_to_env)  # noqa: E402
from hta.world.instances import draw_hstar, instance0  # noqa: E402
from hta.world.language import build_tableau  # noqa: E402


def _spec():
    return instance0()


def test_probe_charges_cost_and_blocks_unprobeable_and_unaffordable():
    spec = _spec()
    st = EpisodeState(spec, draw_hstar(spec, 1))
    valley_cols = [i for i, c in enumerate(st.cells) if c[0] == "valley"]
    direct_cols = [i for i, c in enumerate(st.cells) if c[0] == "direct"]
    # a valley cell is inference-only -> rejected, not charged
    r = st.probe(valley_cols[0])
    assert r["value"] is None and "not a probeable" in r["error"] and st.used == 0
    # a real probe charges its cost
    r = st.probe(direct_cols[0])
    assert r["value"] is not None and st.used == 1 and r["remaining"] == spec.budget - 1
    # spend the rest, then an affordable-looking probe past budget is rejected
    for c in direct_cols[1:spec.budget]:
        st.probe(c)
    assert st.remaining_cost() == 0
    r = st.probe(direct_cols[0] if len(direct_cols) > spec.budget else valley_cols[0])
    assert r["value"] is None


def test_floor_play_scores_about_zero_of_the_band():
    spec = _spec()
    st = EpisodeState(spec, draw_hstar(spec, 2))
    walkable = sorted((c for c in st.cov_cols if c in st._probe_set), key=lambda c: st.costs[c])
    for c in walkable:
        if st.costs[c] > st.remaining_cost():
            break
        st.probe(c)
    st.submit_map({e["col"]: e["value"] for e in st.log})
    sc = st.score()
    assert sc["norm"] == 0.0 and sc["raw"] == sc["floor"]       # floor play == bottom of the band


def test_reconstructing_the_trail_scores_in_band():
    # Scout the gate, walk the live chain, reconstruct the valley by the LOOKUP law -> in-band score.
    spec = _spec()
    hstar = draw_hstar(spec, 3)
    st = EpisodeState(spec, hstar)
    fork = spec.forks()[0]
    # probe the gate + the live chain's variables (their pos-0 sig cells)
    sig_col = {c[1]: i for i, c in enumerate(st.cells) if c[0] == "sig" and c[2] == 0}
    live = fork.live_chain(spec.K, hstar).walk(spec.K, hstar)
    for var in (fork.gate, *live):
        st.probe(sig_col[var])
    # reconstruct EVERY coverage cell the probes now pin, by the public value law
    from hta.world.grade import observed_belief
    table, cells, _, cov, _ = build_tableau(spec)
    H = observed_belief(table, st.log)
    rep = next(iter(H))
    sub = {c: table[rep][c] for c in cov if all(table[h][c] == table[rep][c] for h in H)}
    st.submit_map(sub)
    sc = st.score()
    assert sc["raw"] >= fork.Lv                                  # at least the whole valley earned
    assert sc["norm"] > 0.0


def test_spawn_carveout_charges_only_what_the_worker_spends():
    spec = _spec()
    st = EpisodeState(spec, draw_hstar(spec, 4))
    granted = st.grant_spawn(2)
    assert granted == 2
    # the worker "spent" 1 of its 2 and observed one cell -> only 1 is committed, obs merged
    r = st.commit_spawn("scout", observations=[[0, 1]], used=1, report="found col0=1")
    assert st.used == 1 and r["used"] == 1 and r["remaining"] == spec.budget - 1
    assert any(e["via"] == "worker" and e["col"] == 0 for e in st.log)


def test_env_roundtrip_preserves_world_and_score():
    spec = _spec()
    hstar = draw_hstar(spec, 5)
    env = state_to_env(spec, hstar, spec.budget)
    st = state_from_env(env)
    assert st.spec == spec and st.hstar == hstar and st.budget == spec.budget
    # a SITUATION prefix is replayed (charged + logged)
    import json
    env2 = dict(env)
    direct_col = next(i for i, c in enumerate(spec.cells()) if c[0] == "direct")
    env2["HTA_SITUATION"] = json.dumps({"probed": [direct_col], "mem": "note"})
    st2 = state_from_env(env2)
    assert st2.used == 1 and st2.mem == "note" and len(st2.log) == 1
