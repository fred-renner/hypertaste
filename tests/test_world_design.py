"""Tests for the world-growth design (WORLD_DESIGN.md, Axes A + B).

These cover the new growth machinery without any API cost:
  * compositional rules round-trip through validate -> compile -> score (Axis A);
  * the generative/sampled hypothesis space is safe + deterministic (Axis B), and
    info-gain stays non-zero on a compositional world whose rule is outside the
    25-template library;
  * the solvability gate rejects degenerate (constant) rules;
  * the behavior-vector novelty gate de-dups near-duplicate worlds;
  * the transfer distribution is independently seeded (not weak-tag conditioned),
    deterministic, and only contains admissible (solvable + non-degenerate) worlds.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.config import Config  # noqa: E402
from hta.world import grammar, world_smith  # noqa: E402
from hta.world.engine import WiltWorld  # noqa: E402


# ---------------------------------------------------------------------------
# Axis A: compositional rules are first-class
# ---------------------------------------------------------------------------
def test_compositional_rule_roundtrips():
    """A regime rule validates, compiles, evaluates per-region, and scores by the
    same empirical-equivalence scorer as any atomic rule (scorer unchanged)."""
    src = "lambda x, y, z: (x < y < z) if x < 0 else (x > y > z)"
    assert grammar.validate_lambda(src) is True
    fn = grammar.compile_rule(src)
    assert fn(-3, -2, -1) is True   # x<0 regime -> increasing
    assert fn(3, 2, 1) is True      # x>=0 regime -> decreasing
    assert fn(1, 2, 3) is False     # x>=0 regime but increasing -> False

    world = WiltWorld(grammar.RuleSpec("regime", src, 4, ("ordering",), "regime"))
    assert world.score_guess(src)["solved"] is True                       # equivalent
    assert world.score_guess("lambda x, y, z: x < y < z")["solved"] is False  # not


def test_structure_field_roundtrips():
    """RuleSpec carries `structure` and it survives to_dict/from_dict, and the
    library now contains compositional seeds across all structures."""
    r = grammar.RuleSpec("e", "lambda x, y, z: x < y < z and not (z - x == 4)",
                         5, ("falsification",), "exception")
    assert grammar.RuleSpec.from_dict(r.to_dict()).structure == "exception"
    structures = {c.structure for c in grammar.candidate_library()}
    assert {"atomic", "conjunction", "regime", "exception"} <= structures


# ---------------------------------------------------------------------------
# Axis B: sampled hypothesis space + info-gain
# ---------------------------------------------------------------------------
def test_sample_hypotheses_safe_and_deterministic():
    a = grammar.sample_hypotheses(123, 30, include_library=False)
    b = grammar.sample_hypotheses(123, 30, include_library=False)
    assert [r.source for r in a] == [r.source for r in b]   # reproducible per seed
    assert len(a) == 30
    for r in a:
        assert grammar.validate_lambda(r.source) is True    # safe by construction
        r.fn(0, 1, 2)                                        # compiles + runs
    # max_structure caps complexity
    atomic = grammar.sample_hypotheses(1, 20, max_structure="atomic", include_library=False)
    assert all(r.structure == "atomic" for r in atomic)


def test_info_gain_nonzero_on_compositional_world():
    """The metric measures version-space collapse over the world's SAMPLED hypothesis
    space, so a compositional rule outside the library still yields real info-gain."""
    src = "lambda x, y, z: (x < y < z) and (x % 2 == 0)"   # conjunction, not a library template
    assert src not in {c.source for c in grammar.candidate_library()}
    world = WiltWorld(grammar.RuleSpec("c", src, 3, ("ordering", "parity"), "conjunction"))
    fn = grammar.compile_rule(src)
    triples = [(1, 2, 3), (2, 3, 4), (3, 2, 1), (-1, 0, 1), (2, 2, 2), (0, 1, 2), (-4, -3, -2)]
    history = [{"triple": list(t), "label": fn(*t)} for t in triples]
    hyp = world.hypothesis_reduction(history)
    assert hyp["start"] > len(grammar.candidate_library())   # sampled space, not the library
    assert hyp["avg_info_gain"] > 0.0
    assert hyp["reduced_frac"] > 0.0


# ---------------------------------------------------------------------------
# Solvability gate
# ---------------------------------------------------------------------------
def test_solvability_gate_rejects_constant():
    const_true = grammar.RuleSpec("ct", "lambda x, y, z: x == x", 1, ())   # always True
    const_false = grammar.RuleSpec("cf", "lambda x, y, z: x != x", 1, ())  # always False
    assert world_smith.is_admissible(const_true) is False
    assert world_smith.is_admissible(const_false) is False
    # a non-degenerate, solvable rule passes the same gate
    good = grammar.RuleSpec("inc", "lambda x, y, z: x < y < z", 1, ("ordering",))
    assert world_smith.is_admissible(good) is True


# ---------------------------------------------------------------------------
# Behavior-vector novelty
# ---------------------------------------------------------------------------
def test_near_duplicate_worlds_deduped():
    r1 = grammar.RuleSpec("a", "lambda x, y, z: x < y < z", 1, ("ordering",))
    r2 = grammar.RuleSpec("b", "lambda x, y, z: x < y and y < z", 1, ("ordering",))  # same behavior
    r3 = grammar.RuleSpec("c", "lambda x, y, z: x > y > z", 1, ("ordering",))         # distinct
    # r1 and r2 are behavioral duplicates (identical label over the battery)
    assert world_smith._hamming(world_smith._behavior(r1), world_smith._behavior(r2)) == 0
    # asked for 2 worlds, the gate skips the duplicate and keeps the distinct pair
    chosen = world_smith.select_worlds([r1, r2, r3], n=2)
    assert [r.name for r in chosen] == ["a", "c"]


# ---------------------------------------------------------------------------
# Independently-seeded transfer distribution
# ---------------------------------------------------------------------------
def test_transfer_suite_independent_and_admissible():
    cfg = Config.testing()
    a = [w.rule.source for w in world_smith.transfer_suite(cfg)]
    b = [w.rule.source for w in world_smith.transfer_suite(cfg)]
    assert a == b                              # deterministic, fixed-seed draw
    assert len(a) == cfg.n_transfer_worlds
    for w in world_smith.transfer_suite(cfg):  # every held-out world is solvable
        assert world_smith.is_admissible(w.rule) is True


def test_build_worlds_admissible_and_distinct(tmp_path):
    cfg = Config.testing()
    cfg.backend = "mock"
    cfg.out_dir = str(tmp_path)
    worlds = world_smith.build_worlds(cfg, target_difficulty=3, weak_tags=["ordering"],
                                      log=lambda *a, **k: None)
    assert len(worlds) == cfg.n_train_worlds
    for w in worlds:
        assert world_smith.is_admissible(w.rule) is True
    vecs = [world_smith._behavior(w.rule) for w in worlds]
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            assert world_smith._hamming(vecs[i], vecs[j]) >= world_smith._NOVELTY_HAMMING
