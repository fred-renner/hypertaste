"""World-language tests — the part-box, the validator, the deterministic expander (hta/world/
language.py). Deterministic, pure compute, no API cost.

The load-bearing claims:
- A parts-list compiles to a bounded, deterministic tableau; signposts are instruments (probeable,
  not coverage), clearings are immediate (probeable + coverage), valleys are inference-only (coverage,
  not probeable).
- Reconstruction stays a LOOKUP (B2), but a fork's valley is GATED: it is determined iff the gate
  (which chain is live) AND the live chain's variables are pinned. Walking a chain WITHOUT the gate
  pins zero valley — the structural strategy-trap.
- A gate LADDER needs every rung scouted, not just the first.
- A single-chain fork degenerates (the gate carries no information).
- The validator catches malformed structure; the public face hides values but exposes the law.
- Multiple regions COMPOSE (the thing that makes this a language, not a fixed world).
"""

import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.world.language import (Chain, Clearing, Fork, WorldSpec, build_tableau,  # noqa: E402
                                public_cells, validate)

# A small forked world (256 hypotheses): two depth-2 chains + a gate + one clearing.
FORK = WorldSpec("fork-small", R=8, K=2, budget=4, regions=(
    Fork(gate=0, Lv=9, chains=(Chain(1, ((2, 3),)), Chain(4, ((5, 6),)))), Clearing(7)))
SINGLE = WorldSpec("single-small", R=8, K=2, budget=4, regions=(
    Fork(gate=0, Lv=9, chains=(Chain(1, ((2, 3),)),)), Clearing(4), Clearing(5)))
# A small gate LADDER (gate 0 -> final gate 1 or 2) selecting one of two chains.
LADDER = WorldSpec("ladder-small", R=8, K=2, budget=4, regions=(
    Fork(gate=0, Lv=9, gate_hops=((1, 2),), chains=(Chain(3, ()), Chain(4, ()))),
    Clearing(5), Clearing(6), Clearing(7)))


def _hyps(spec):
    return list(itertools.product(range(spec.K), repeat=spec.R))


def _live(spec, fork, h):
    return fork.live_chain(spec.K, h).walk(spec.K, h)


def test_expander_deterministic_and_bounded():
    table, cells, costs, cov, probe = build_tableau(FORK)
    assert len(table) == FORK.K ** FORK.R              # one row per hypothesis
    assert all(len(row) == FORK.M for row in table)    # one column per cell
    assert all(0 <= v < FORK.K for row in table for v in row)
    assert build_tableau(FORK)[0] == table             # deterministic
    valley = [i for i, c in enumerate(cells) if c[0] == "valley"]
    sig = [i for i, c in enumerate(cells) if c[0] == "sig"]
    direct = [i for i, c in enumerate(cells) if c[0] == "direct"]
    assert valley and all(i in cov and i not in probe for i in valley)    # inference-only
    assert sig and all(i in probe and i not in cov for i in sig)          # instruments
    assert direct and all(i in probe and i in cov for i in direct)        # immediate bait


def test_value_law_is_a_lookup():
    # A cell's value is a deterministic lookup of its variable's hidden value, never a pattern to
    # guess: signpost/clearing -> (var + pos) mod K; once the var is pinned the cell is forced.
    table, cells, costs, cov, probe = build_tableau(FORK)
    hyps = _hyps(FORK)
    for col, c in enumerate(cells):
        if c[0] in ("sig", "direct"):
            _, var, pos = c
            for hi, h in enumerate(hyps):
                assert table[hi][col] == (h[var] + pos) % FORK.K


def test_gate_is_necessary_walking_the_live_chain_alone_pins_no_valley():
    table, cells, costs, cov, probe = build_tableau(FORK)
    fork = FORK.forks()[0]
    hyps = _hyps(FORK)
    h = hyps[0]
    live = _live(FORK, fork, h)
    valley_cols = tuple(i for i, c in enumerate(cells) if c[0] == "valley")
    no_gate = frozenset(i for i, hh in enumerate(hyps) if all(hh[r] == h[r] for r in live))
    with_gate = frozenset(i for i, hh in enumerate(hyps) if all(hh[r] == h[r] for r in (fork.gate, *live)))
    from hta.world.grade import determined
    assert determined(table, valley_cols, no_gate) == 0
    assert determined(table, valley_cols, with_gate) == fork.Lv


def test_gate_ladder_requires_scouting_every_rung_not_just_the_first():
    table, cells, costs, cov, probe = build_tableau(LADDER)
    fork = LADDER.forks()[0]
    hyps = _hyps(LADDER)
    h = hyps[0]
    ladder = fork.gate_chain(LADDER.K, h)
    assert len(ladder) == 2 and ladder[0] == fork.gate and ladder[-1] == fork.final_gate(LADDER.K, h)
    live = _live(LADDER, fork, h)
    valley_cols = tuple(i for i, c in enumerate(cells) if c[0] == "valley")
    first_only = frozenset(i for i, hh in enumerate(hyps) if all(hh[r] == h[r] for r in (fork.gate, *live)))
    whole = frozenset(i for i, hh in enumerate(hyps) if all(hh[r] == h[r] for r in (*ladder, *live)))
    from hta.world.grade import determined
    assert determined(table, valley_cols, first_only) == 0       # first gate alone -> nothing
    assert determined(table, valley_cols, whole) == fork.Lv      # whole ladder + chain -> valley


def test_single_chain_gate_is_degenerate():
    fork = SINGLE.forks()[0]
    hyps = _hyps(SINGLE)
    h = hyps[0]
    assert fork.gate not in fork.trail_regs(SINGLE.K, h)         # gate excluded when no real fork
    table, cells, costs, cov, probe = build_tableau(SINGLE)
    chain_regs = fork.chains[0].walk(SINGLE.K, h)
    valley_cols = tuple(i for i, c in enumerate(cells) if c[0] == "valley")
    H = frozenset(i for i, hh in enumerate(hyps) if all(hh[r] == h[r] for r in chain_regs))
    from hta.world.grade import determined
    assert determined(table, valley_cols, H) == fork.Lv


def test_multiple_regions_compose():
    # Two forks + a clearing over a shared variable pool: each fork's valley mirrors ITS OWN live
    # chain (the per-region resolution that makes this a language, not a single fork). The cell layout
    # carries both valleys, tagged with their region indices.
    spec = WorldSpec("two-fork", R=8, K=2, budget=5, regions=(
        Fork(gate=0, Lv=3, chains=(Chain(1, ()), Chain(2, ()))),   # fork at region 0
        Fork(gate=3, Lv=3, chains=(Chain(4, ()), Chain(5, ()))),   # fork at region 1
        Clearing(6), Clearing(7)))
    assert validate(spec) == []
    cells = spec.cells()
    valley_regions = sorted({c[1] for c in cells if c[0] == "valley"})
    assert valley_regions == [0, 1]                                # both forks contribute a valley
    table, _, _, cov, probe = build_tableau(spec)
    assert len(table) == 2 ** 8
    # each valley resolves under its own fork's gate+chain, independently
    h = (0,) * 8
    for idx, fork in ((0, spec.regions[0]), (1, spec.regions[1])):
        lm = fork.landmark_reg(spec.K, h)
        vcols = [i for i, c in enumerate(cells) if c[0] == "valley" and c[1] == idx]
        for col in vcols:
            pos = cells[col][2]
            assert table[0][col] == (h[lm] + pos) % spec.K


def test_validate_catches_malformed_structure():
    assert validate(FORK) == []
    bad = WorldSpec("bad", R=8, K=2, budget=3, regions=(
        Fork(gate=99, Lv=9, chains=(Chain(1, ((2, 99),)),)), Clearing(3)))   # gate + hop out of range
    issues = validate(bad)
    assert any("gate" in m for m in issues) and any("out of range" in m for m in issues)
    no_clear = WorldSpec("nc", R=3, K=2, budget=2, regions=(   # all regs are signposts
        Fork(gate=0, Lv=9, chains=(Chain(1, ((2, 0),)),)),))
    assert any("clearing" in m for m in validate(no_clear))
    overlap = WorldSpec("ov", R=8, K=2, budget=3, regions=(    # var 1 is signpost AND clearing
        Fork(gate=0, Lv=9, chains=(Chain(1, ()),)), Clearing(1), Clearing(2)))
    assert any("disjoint" in m for m in validate(overlap))


def test_serialization_round_trips():
    import json
    for spec in (FORK, SINGLE, LADDER):
        d = json.loads(json.dumps(spec.to_dict()))
        assert WorldSpec.from_dict(d) == spec


def test_world_map_public_hides_values_but_exposes_the_law():
    wm = FORK.world_map_public(remaining=3)
    assert wm["R"] == 8 and wm["K"] == 2 and wm["remaining"] == 3
    rule = wm["value_rule"]
    assert "lookup" in rule and "hidden value" in rule and "live" in rule.lower()
    fork_region = next(r for r in wm["regions"] if r["kind"] == "fork")
    assert fork_region["gate"] == 0 and fork_region["n_chains"] == 2
    # public descriptors only, generic vocabulary: cells carry cost/role flags, never a hidden value
    assert all(set(c) <= {"col", "cost", "probeable", "coverage", "var", "pos", "region", "mirrors"}
               for c in wm["cells"])
