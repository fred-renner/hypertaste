"""Tests for the Pass-3 hidden-map family (hta/ch2/hidden_map.py): the enumerable
topology-x-values hypothesis space, the spec-owned value law riding anchor.py's generic tableau
protocol, the zero no-inference floor (probeable and coverage cells disjoint), the public face
(no hidden values), and the build-screen gates on a tiny family. The full canonical screen is
run_hiddenmap.py's job (slow-ish); tests stay on small specs."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.ch2 import anchor, hidden_map as hm  # noqa: E402
from hta.ch2.hidden_map import GroupSpec, HiddenMapSpec  # noqa: E402


def tiny_spec() -> HiddenMapSpec:
    """One deep coupled group (hidden depth 1..2), one bait. 2*2 paths... deep paths: lengths
    1 (2 ways) + 2 (4 ways) = 6; vars (6, 2, 1, 2, 2) -> 48 hypotheses."""
    return HiddenMapSpec(
        name="tiny",
        groups=(GroupSpec(layers=(2, 2), region_len=4, coupled=True),
                GroupSpec(layers=(), region_len=2, coupled=False)),
        budget=4)


# ---------------------------------------------------------------------------
# The hypothesis space: public, enumerable, a product of per-variable ranges.
# ---------------------------------------------------------------------------
def test_variable_ranges_and_enumeration():
    spec = tiny_spec()
    assert spec.variable_ranges() == (6, 2, 1, 2, 2)
    hyps = list(spec.hypotheses())
    assert len(hyps) == spec.n_hyps() == 48
    assert len(set(hyps)) == 48


def test_paths_enumerate_every_stop_depth():
    g = GroupSpec(layers=(2, 2))
    paths = g.paths()
    assert len(paths) == 6                      # 2 one-hop + 4 two-hop
    assert {len(p) for p in paths} == {1, 2}
    assert GroupSpec(layers=()).paths() == [()]


# ---------------------------------------------------------------------------
# The value law: links encode the realized shape, regions need key+backbone+length.
# ---------------------------------------------------------------------------
def test_value_law_links_keys_regions():
    spec = tiny_spec()
    paths = spec.groups[0].paths()
    # hyp: deep path = (1, 0) (via layer-1 candidate 1, stop at layer-2 candidate 0),
    # deep key 1, bait path trivial, bait key 0, backbone 1
    hyp = (paths.index((1, 0)), 1, 0, 0, 1)
    assert spec.value(("link", 0, 0, 0), hyp) == 2 + 1     # entry -> candidate 1
    assert spec.value(("link", 0, 1, 0), hyp) == 0         # off the realized path
    assert spec.value(("link", 0, 1, 1), hyp) == 2 + 0     # on path -> layer-2 candidate 0
    assert spec.value(("key", 0), hyp) == 1
    assert spec.value(("key", 1), hyp) == 0
    assert spec.value(("backbone",), hyp) == 1
    # deep region: (key 1 + backbone 1 + length 2 + pos) % 2
    assert spec.value(("region", 0, 0), hyp) == 0
    assert spec.value(("region", 0, 1), hyp) == 1
    # bait region is uncoupled, length 0: (key 0 + pos) % 2
    assert spec.value(("region", 1, 0), hyp) == 0


def test_link_reads_stop_at_the_terminus():
    spec = tiny_spec()
    paths = spec.groups[0].paths()
    hyp = (paths.index((0,)), 0, 0, 0, 0)                   # depth-1 path via candidate 0
    assert spec.value(("link", 0, 1, 0), hyp) == 1          # the path stops here
    assert spec.value(("link", 0, 1, 1), hyp) == 0          # off-path


# ---------------------------------------------------------------------------
# The tableau protocol: anchor.py machinery rides the spec unchanged.
# ---------------------------------------------------------------------------
def test_tableau_probeable_and_coverage_are_disjoint_floor_zero():
    spec = tiny_spec()
    table, cells, costs, cov, probe = anchor.build_tableau(spec)
    assert len(table) == 48 and len(table[0]) == len(cells)
    assert set(cov) & set(probe) == set()                   # no probeable coverage cell ->
    assert anchor.floor_value(spec) == 0.0                  # the no-inference floor is exactly 0


def test_oracle_between_best_planner_and_total_coverage():
    spec = tiny_spec()
    oracle = anchor.oracle_value(spec)
    heur = max(anchor._simulate(spec, pick) for pick in anchor.BASKET.values())
    total = sum(g.region_len for g in spec.groups)
    assert heur <= oracle + 1e-9 <= total
    assert oracle > 0


def test_anchor_specs_unchanged_by_the_protocol_extension():
    from hta.ch2.episode_state import canonical_spec
    spec = canonical_spec()
    table, cells, costs, cov, probe = anchor.build_tableau(spec)
    assert len(table) == spec.K ** spec.R                   # trail default enumeration intact
    assert anchor.floor_value(spec) == 3.0                  # the anchor's known floor


# ---------------------------------------------------------------------------
# The public face: structure only, never hidden values.
# ---------------------------------------------------------------------------
def test_world_map_public_exposes_structure_not_values():
    spec = tiny_spec()
    wm = spec.world_map_public(remaining=3)
    assert wm["remaining"] == 3 and wm["n_groups"] == 2
    assert "goals" not in wm                                # multi-goal present but off
    by_kind = {}
    for e in wm["cells"]:
        by_kind.setdefault(e["kind"], []).append(e)
        assert e["probeable"] == (e["kind"] != "region")
        assert e["coverage"] == (e["kind"] == "region")
        assert "value" not in e
    assert set(by_kind) == {"link", "key", "backbone", "region"}
    assert len(spec.goals()) == 1
    assert spec.goals()[0]["region_cols"] == [e["col"] for e in by_kind["region"]]


def test_serialization_round_trip_and_kind_dispatch():
    from hta.ch2.episode_state import spec_from_dict
    spec = tiny_spec()
    d = spec.to_dict()
    assert d["kind"] == "hidden"
    assert HiddenMapSpec.from_dict(d) == spec
    assert spec_from_dict(d) == spec


def test_validate_rejects_malformed_and_unenumerable():
    assert hm.validate(tiny_spec()) == []
    assert hm.validate(HiddenMapSpec("bad", groups=(), budget=3))
    assert hm.validate(HiddenMapSpec(
        "bad", groups=(GroupSpec(layers=(0,)),), budget=3))
    big = HiddenMapSpec("big", groups=(GroupSpec(layers=(4, 4, 4, 4), region_len=4),) * 3,
                        budget=3)
    assert any("too large" in i for i in hm.validate(big))


# ---------------------------------------------------------------------------
# The build-screen on the tiny family: gates behave, controls separate.
# ---------------------------------------------------------------------------
def test_screen_gates_on_tiny_family():
    s = hm.screen(tiny_spec())
    assert s["valid"] and s["no_free_coverage"] and s["floor"] == 0.0
    assert 0 <= s["heur_norm"] <= 1 and s["method_norm"] <= 1 + 1e-9
    assert s["cliff"] == 4 / 6


def test_screen_control_reads_no_gap():
    bait = GroupSpec(layers=(), region_len=2, coupled=False)
    s = hm.screen(HiddenMapSpec("flat", groups=(bait, bait), budget=2))
    assert s["gap_norm"] <= 1e-9 and not s["hard"]          # myopic play is optimal -> below


def test_reference_method_solves_tiny():
    s = hm.screen(tiny_spec())
    assert s["method_norm"] >= s["heur_norm"] - 1e-9        # the witness at least matches planners
