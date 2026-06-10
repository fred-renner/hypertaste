"""Tests for the frozen episode-state machine + the band judge (hta/ch2/episode_state.py) — the
substrate the model-orchestrated harness confines the player to. Pure, deterministic, no API cost:
this is where the airgap (values only through probe), the cost-budget accounting, the spawn
carve-out, and the ungameable coverage judge are proven without a live claude.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.ch2 import anchor  # noqa: E402
from hta.ch2.episode_state import EpisodeState, normalize  # noqa: E402

# A small, fast trail (matches tests/test_anchor.py's TRAIL): 256 hypotheses, budget 3.
SPEC = anchor.TrailSpec("trail-small", R=8, K=2, Ld=2, Lv=9, trailhead=0,
                        waypoints=(1, 2), landmarks=((3, 4), (3, 4)), budget=3)
HSTAR = (1, 0, 1, 0, 1, 0, 1, 0)


def sig_col(st, reg):
    for i, c in enumerate(st.cells):
        if c[0] == "sig" and c[1] == reg:
            return i
    raise AssertionError(f"no signpost cell for register {reg}")


def valley_cols(st):
    return [i for i, c in enumerate(st.cells) if c[0] == "valley"]


def clearing_cols(st):
    return [i for i, c in enumerate(st.cells) if c[0] == "direct"]


def test_probe_charges_cost_and_logs():
    st = EpisodeState(SPEC, HSTAR)
    col = clearing_cols(st)[0]
    r = st.probe(col)
    assert r["value"] == anchor.cell_value(SPEC, st.cells[col], HSTAR)
    assert r["cost"] == 1 and r["remaining"] == SPEC.budget - 1
    assert st.log == [{"col": col, "value": r["value"], "cost": 1, "via": "self"}]


def test_malformed_and_unaffordable_probes_are_not_charged():
    st = EpisodeState(SPEC, HSTAR)
    assert st.probe(9999)["error"]                       # out of range
    assert st.probe(valley_cols(st)[0])["error"]          # valley is inference-only, not probeable
    assert st.probe(True)["error"]                        # bool is not an index
    assert st.used == 0                                   # none of those charged
    # drain the budget, then an affordable-cost probe is refused for lack of budget
    for c in clearing_cols(st)[:SPEC.budget]:
        st.probe(c)
    assert st.remaining_cost() == 0
    assert "insufficient budget" in st.probe(clearing_cols(st)[SPEC.budget])["error"]


def test_world_map_is_public_only_no_value_leak():
    st = EpisodeState(SPEC, HSTAR)
    wm = st.world_map()
    # the link chain is public (generic vocabulary: variable/value, cells/links)
    assert wm["links"]["root"] == 0 and wm["links"]["level1"] == [1, 2]
    # the layout is public; no cell carries its hidden value
    assert all("value" not in cell for cell in wm["cells"])
    # role falls out of the generic flags, never a world-story kind label
    assert all("kind" not in cell for cell in wm["cells"])
    assert any(c.get("mirrors") == "target" and not c["probeable"] and c["coverage"]
               for c in wm["cells"])
    assert any("var" in c and c["probeable"] and not c["coverage"] for c in wm["cells"])


def test_world_map_exposes_value_law_but_not_the_seed():
    """Calibration legibility: the deterministic VALUE LAW is public (so reconstruction is a
    reachable lookup, not a guess), while the hidden variable values never appear. The deep cells
    flag that they mirror the link-resolved target variable."""
    st = EpisodeState(SPEC, HSTAR)
    wm = st.world_map()
    assert "value_rule" in wm and "mod K" in wm["value_rule"]
    cov_only = [c for c in wm["cells"] if c["coverage"] and not c["probeable"]]
    assert cov_only and all(c.get("mirrors") == "target" for c in cov_only)
    # the law is structure, never the seed: no variable value is recoverable from the map
    blob = json.dumps(wm)
    assert "hstar" not in blob and str(list(HSTAR)) not in blob


def test_mem_patch_is_incremental_append_edit_delete():
    st = EpisodeState(SPEC, HSTAR)
    st.mem_patch(replace="trail: trailhead=0")           # append (no find)
    st.mem_patch(replace="lead: col5 looks fat")
    assert "trail" in st.mem and "lead" in st.mem
    assert st.mem_patch(find="lead: col5 looks fat", replace="retracted: col5 was a clearing")["ok"]
    assert "retracted" in st.mem and "looks fat" not in st.mem      # edit (revision)
    assert st.mem_patch(find="retracted: col5 was a clearing", replace="")["ok"]
    assert "retracted" not in st.mem                                # delete (forgetting)
    assert not st.mem_patch(find="absent", replace="x")["ok"]       # find not present


def test_submit_map_parses_dict_and_list_rejects_garbage():
    st = EpisodeState(SPEC, HSTAR)
    assert st.submit_map({0: 1, "2": 0})["accepted"]
    assert st.submitted == {0: 1, 2: 0}
    assert st.submit_map([0, 1, 0])["accepted"]            # flat list -> cov columns in order
    assert not st.submit_map("nonsense")["accepted"]
    assert not st.submit_map({0: True})["accepted"]        # bool is not a value


def test_floor_player_scores_at_the_floor():
    # Probe the cheapest coverage cells (clearings) and submit them: the no-inference floor.
    st = EpisodeState(SPEC, HSTAR)
    for c in clearing_cols(st)[:SPEC.budget]:
        st.probe(c)
    st.submit_map({e["col"]: e["value"] for e in st.log})
    s = st.score()
    assert s["raw"] == anchor.floor_value(SPEC)
    assert s["norm"] == 0.0


def test_walking_the_trail_pins_the_valley_and_reaches_the_oracle():
    # The optimal policy: spend all 3 probes on the trail's signposts; that pins the whole valley
    # (a lookup), which no clearing-grab can match -> raw == oracle, norm == 1.0.
    st = EpisodeState(SPEC, HSTAR)
    for reg in SPEC.trail_regs(HSTAR):
        st.probe(sig_col(st, reg))
    submission = {c: anchor.cell_value(SPEC, st.cells[c], HSTAR) for c in valley_cols(st)}
    st.submit_map(submission)
    s = st.score()
    assert s["raw"] == anchor.oracle_value(SPEC) == SPEC.Lv
    assert s["norm"] == 1.0


def test_coverage_is_ungameable_guessing_unpinned_cells_earns_nothing():
    # Probe the 3 clearings (pinning them), then ALSO guess every valley cell. The valley is not
    # pinned by clearing probes, so the guesses earn zero — the score counts only pinned+correct.
    st = EpisodeState(SPEC, HSTAR)
    for c in clearing_cols(st)[:SPEC.budget]:
        st.probe(c)
    submission = {e["col"]: e["value"] for e in st.log}
    submission.update({c: anchor.cell_value(SPEC, st.cells[c], HSTAR) for c in valley_cols(st)})
    assert st.submit_map(submission)["accepted"]
    assert st.score()["raw"] == anchor.floor_value(SPEC)   # the valley guesses added nothing


def test_no_submission_is_worst_score():
    st = EpisodeState(SPEC, HSTAR)
    for reg in SPEC.trail_regs(HSTAR):
        st.probe(sig_col(st, reg))
    assert st.coverage_raw() == 0                           # pinned the valley but never submitted
    assert st.score()["norm"] == 0.0


def test_spawn_grant_and_commit_accounting():
    st = EpisodeState(SPEC, HSTAR)
    assert st.grant_spawn(2) == 2                            # min(req, remaining)
    assert st.grant_spawn(99) == st.remaining_cost()        # capped to remaining
    # a worker reports two observations and spent 2 of its carve-out; only `used` is charged
    obs = [[sig_col(st, SPEC.trail_regs(HSTAR)[0]), 1], [sig_col(st, SPEC.trail_regs(HSTAR)[1]), 0]]
    res = st.commit_spawn("walk the trail", obs, used=2, report="found two signposts")
    assert res["used"] == 2 and st.remaining_cost() == SPEC.budget - 2
    assert [e["via"] for e in st.log] == ["worker", "worker"]   # merged into the global log
    assert st.spawns[0]["n_obs"] == 2


def test_worker_observations_count_toward_coverage():
    # A worker walks the whole trail; the top folds in its observations and submits the valley.
    st = EpisodeState(SPEC, HSTAR)
    obs = [[sig_col(st, reg), anchor.cell_value(SPEC, st.cells[sig_col(st, reg)], HSTAR)]
           for reg in SPEC.trail_regs(HSTAR)]
    st.commit_spawn("walk the full trail", obs, used=3)
    st.submit_map({c: anchor.cell_value(SPEC, st.cells[c], HSTAR) for c in valley_cols(st)})
    assert st.score()["raw"] == SPEC.Lv                     # the worker's probes pinned the valley


def test_normalize_clips_to_unit_band():
    assert normalize(3, 3, 9) == 0.0
    assert normalize(9, 3, 9) == 1.0
    assert normalize(0, 3, 9) == 0.0                        # below floor clips to 0
    assert normalize(12, 3, 9) == 1.0                       # above oracle clips to 1
