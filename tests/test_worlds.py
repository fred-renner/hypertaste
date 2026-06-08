"""Forked-trail world tests — the world-smith's structural family (`hta/ch2/worlds.py`).
Deterministic, pure compute, no API cost.

The load-bearing claims (the structural lift of `test_anchor.py`):
- The forked spec implements the same protocol the anchor does, so the *unchanged*, structure-agnostic
  oracle/screen machinery (`build_tableau`/`oracle_value`/`screen`) re-derives the referee mechanically
  — the integrity wall lifted to the second loop (the inventor proposes structure; the score is never
  authored).
- Reconstruction stays a LOOKUP (B2), but gated: the valley is determined iff the GATE (which chain is
  live) AND the live chain's registers are pinned. Walking a chain WITHOUT the gate pins zero valley —
  the structural strategy-trap that demands scout-then-commit.
- The single-chain spec degenerates to the anchor's policy (the gate carries no information): the valley
  is pinned by walking the one trail, gate or no gate.
- Structure realized from validated DATA round-trips (safe-eval lifted: never code, never the score).
"""

import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.ch2 import anchor  # noqa: E402
from hta.ch2.worlds import Chain, ForkedTrailSpec, decoy_spec, single_chain_spec, validate  # noqa: E402

# A small forked world (256 hypotheses) for the structural tests: two depth-2 chains + a gate.
FORK = ForkedTrailSpec("fork-small", R=8, K=2, Ld=2, Lv=9, gate=0,
                       chains=(Chain(1, ((2, 3),)), Chain(4, ((5, 6),))), budget=4)
SINGLE = ForkedTrailSpec("single-small", R=8, K=2, Ld=2, Lv=9, gate=0,
                         chains=(Chain(1, ((2, 3),)),), budget=4)


def _hyps(spec):
    return list(itertools.product(range(spec.K), repeat=spec.R))


def test_expander_deterministic_and_bounded():
    table, cells, costs, cov, probe = anchor.build_tableau(FORK)
    assert len(table) == FORK.K ** FORK.R              # one row per hypothesis
    assert all(len(row) == FORK.M for row in table)    # one column per cell
    assert all(0 <= v < FORK.K for row in table for v in row)
    assert anchor.build_tableau(FORK)[0] == table      # deterministic
    # valley = inference-only (coverage but never probeable); signposts = instruments (probe not cov)
    valley = [i for i, c in enumerate(cells) if c[0] == "valley"]
    sig = [i for i, c in enumerate(cells) if c[0] == "sig"]
    assert valley and all(i in cov and i not in probe for i in valley)
    assert sig and all(i in probe and i not in cov for i in sig)


def test_gate_is_necessary_walking_the_live_chain_alone_pins_no_valley():
    # The scout-then-commit core: the valley mirrors the LIVE chain's landmark, and which chain is live
    # is the gate. Pinning the live chain's registers WITHOUT the gate leaves the valley undetermined
    # (the consistent set still spans both gate values); pinning the gate AND the live chain determines
    # all Lv cells. No joint solve anywhere — it stays a lookup, just gated.
    table, cells, costs, cov, probe = anchor.build_tableau(FORK)
    hyps = _hyps(FORK)
    h = hyps[0]
    live = FORK.walk(FORK.chains[FORK.live_index(h)], h)
    valley_cols = tuple(i for i, c in enumerate(cells) if c[0] == "valley")
    no_gate = frozenset(i for i, hh in enumerate(hyps) if all(hh[r] == h[r] for r in live))
    with_gate = frozenset(i for i, hh in enumerate(hyps) if all(hh[r] == h[r] for r in (FORK.gate, *live)))
    assert anchor.determined(table, valley_cols, no_gate) == 0
    assert anchor.determined(table, valley_cols, with_gate) == FORK.Lv


def test_single_chain_gate_is_degenerate():
    # One chain -> gate_value % 1 == 0 always selects it -> the gate is not load-bearing: walking the
    # single trail pins the valley with no gate read (exactly the anchor's policy).
    table, cells, costs, cov, probe = anchor.build_tableau(SINGLE)
    hyps = _hyps(SINGLE)
    h = hyps[0]
    chain_regs = SINGLE.walk(SINGLE.chains[0], h)
    assert SINGLE.gate not in SINGLE.trail_regs(h)     # gate excluded when there is no real fork
    valley_cols = tuple(i for i, c in enumerate(cells) if c[0] == "valley")
    H = frozenset(i for i, hh in enumerate(hyps) if all(hh[r] == h[r] for r in chain_regs))
    assert anchor.determined(table, valley_cols, H) == SINGLE.Lv


def test_reference_ordering_holds():
    s = anchor.screen(FORK)
    assert s["floor"] <= s["best_heur"] <= s["oracle"] <= s["clairvoyant"] + 1e-9
    assert all(s["oracle"] >= h - 1e-9 for h in s["heurs"].values())


def test_decoy_is_above_threshold_and_anti_cliff():
    # The canonical decoy must clear the same build-screen the anchor does: oracle strictly beats every
    # generic planner (incl. 2-step lookahead), with an anti-cliff ramp.
    s = anchor.screen(decoy_spec(), clair=False)
    assert s["oracle"] > s["best_heur"] + 1e-9
    assert s["gap_norm"] >= 0.15
    assert s["heurs"]["lookahead2"] < s["oracle"] - 1e-9
    assert s["ramp_monotone"] and s["ramp_maxstep"] <= 0.55


def test_serialization_round_trips_and_is_kind_tagged():
    import json
    for spec in (FORK, decoy_spec(), single_chain_spec()):
        d = json.loads(json.dumps(spec.to_dict()))
        assert d["kind"] == "forked"
        assert ForkedTrailSpec.from_dict(d) == spec


def test_validate_catches_malformed_structure():
    assert validate(FORK) == []
    bad = ForkedTrailSpec("bad", R=8, K=2, Ld=2, Lv=9, gate=99,            # gate out of range
                          chains=(Chain(1, ((2, 99),)),), budget=3)        # hop target out of range
    issues = validate(bad)
    assert any("gate" in m for m in issues) and any("out of range" in m for m in issues)
    no_clear = ForkedTrailSpec("nc", R=3, K=2, Ld=2, Lv=9, gate=0,        # all regs are signposts
                               chains=(Chain(1, ((2, 0),)),), budget=2)
    assert any("clearing" in m for m in validate(no_clear))


def test_world_map_public_hides_values_but_exposes_the_law():
    wm = FORK.world_map_public(remaining=3)
    assert wm["n_chains"] == 2 and wm["fork"]["gate"] == 0
    assert "LIVE chain" in wm["value_rule"]
    # public descriptors only: cells carry role/cost, never a hidden value
    assert all(set(c) <= {"col", "kind", "cost", "probeable", "coverage", "reg", "pos", "mirrors"}
               for c in wm["cells"])
