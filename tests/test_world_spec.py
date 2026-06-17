"""Tests for the world spec/build (hta/world/spec.py) and the authored seed world.

Two jobs:
  - pin the integrity wall: `validate` rejects every illegal wiring; `build` is deterministic and
    model-free; the hidden answer never leaks through the grader's surface.
  - CERTIFY the seed world ships (the handoff bar): grade_world says it is hard AND solvable, and
    -- the part that makes the gap *taste* and not a fixed tactic -- the exact oracle beats both a
    myopic greedy player and a bounded 2-step planner. The seed world demands depth-3 adaptive
    play with dead-end triage; a shallow formula cannot reach it. Endpoints are hand-checked.
"""

from functools import lru_cache
from pathlib import Path

import pytest

from hta.lab import scoring
from hta.lab.scoring import _determined, _partition, _tableau
from hta.world import spec as wspec
from hta.world.seed.prospect import build_seed, seed_spec


# --------------------------------------------------------------------------- validate
def test_seed_spec_is_valid():
    wspec.validate(seed_spec())            # must not raise


def _bad(mutate):
    s = seed_spec()
    mutate(s)
    with pytest.raises(ValueError):
        wspec.validate(s)


def test_validate_rejects_out_of_range_register():
    _bad(lambda s: s["seams"][0].__setitem__("pointer", 99))


def test_validate_rejects_reused_register():
    # point the vein's pointer at the clearing's register -> two roles for one register.
    _bad(lambda s: s["seams"][0].__setitem__("pointer", 0))


def test_validate_rejects_orphan_register():
    _bad(lambda s: s.__setitem__("R", 11))          # reg 10 declared but unused


def test_validate_rejects_assay_without_noise():
    _bad(lambda s: s["seams"][1].__setitem__("noise", None))


def test_validate_rejects_no_seams():
    _bad(lambda s: s.__setitem__("seams", []))


def test_validate_rejects_bad_kind():
    _bad(lambda s: s.__setitem__("kind", "trail"))


# --------------------------------------------------------------------------- build
def test_build_is_deterministic_and_truth_is_a_hypothesis():
    w0a, w0b, w1 = build_seed(0), build_seed(0), build_seed(1)
    assert w0a.truth == w0b.truth                   # same seed -> same hidden answer
    assert w0a.truth in w0a.hypotheses()
    assert len(w0a.truth) == 10
    # the draw actually varies with the seed (not a fixed constant world)
    assert any(build_seed(s).truth != w0a.truth for s in range(1, 6))


def test_reveal_matches_observe_under_truth():
    w = build_seed(3)
    for p in w.positions():
        assert w.reveal(p) == w.observe(p, w.truth)


# --------------------------------------------------------------------------- the band (certify it ships)
def test_grade_world_hard_and_solvable():
    g = scoring.grade_world(build_seed(0))
    assert (g["floor"], g["oracle"]) == (4.0, 10.0)     # hand-checked endpoints
    assert g["scorable"] == 16
    assert g["gap"] == 6.0 and g["reachable"] == 0.625
    assert g["hard"] is True and g["solvable"] is True


# --------------------------------------------------------------------------- the gap is TASTE, not a tactic
#  Local, throwaway baselines (the richer hardness check is deferred from scoring.py per the
#  handoff). They reuse the grader's belief helpers and never look inside a hypothesis.
def _greedy_myopic(table, costs, scored_cols, probe_cols, budget):
    """1-step planner: each move take the probe with the largest immediate determined-gain/cost."""
    n, total = len(table), 0.0
    for hstar in range(n):
        H, b, probed = frozenset(range(n)), budget, set()
        while True:
            base = _determined(table, scored_cols, H)
            best_c, best = None, 1e-9
            for c in probe_cols:
                if c in probed or costs[c] > b:
                    continue
                groups = _partition(table, H, c)
                if len(groups) == 1:
                    continue
                exp = sum(len(g) / len(H) * _determined(table, scored_cols, g) for g in groups.values())
                if (exp - base) / costs[c] > best:
                    best, best_c = (exp - base) / costs[c], c
            if best_c is None:
                break
            probed.add(best_c); b -= costs[best_c]
            v = table[hstar][best_c]
            H = frozenset(h for h in H if table[h][best_c] == v)
        total += _determined(table, scored_cols, H)
    return total / n


def _lookahead(table, costs, scored_cols, probe_cols, budget, depth):
    """Bounded planner: re-plan each move assuming only `depth` more probes (a truncated belief-MDP)."""
    @lru_cache(maxsize=None)
    def V(H, t, b):
        best = float(_determined(table, scored_cols, H))
        if t == 0:
            return best
        for c in probe_cols:
            if costs[c] > b:
                continue
            groups = _partition(table, H, c)
            if len(groups) == 1:
                continue
            exp = sum(len(g) / len(H) * V(g, t - 1, b - costs[c]) for g in groups.values())
            best = max(best, exp)
        return best

    n, total = len(table), 0.0
    for hstar in range(n):
        H, b, probed = frozenset(range(n)), budget, set()
        while True:
            best_c, best = None, None
            for c in probe_cols:
                if c in probed or costs[c] > b:
                    continue
                groups = _partition(table, H, c)
                if len(groups) == 1:
                    continue
                exp = sum(len(g) / len(H) * V(g, depth - 1, b - costs[c]) for g in groups.values())
                if best is None or exp > best:
                    best, best_c = exp, c
            if best_c is None:
                break
            probed.add(best_c); b -= costs[best_c]
            v = table[hstar][best_c]
            H = frozenset(h for h in H if table[h][best_c] == v)
        total += _determined(table, scored_cols, H)
    return total / n


def test_oracle_beats_myopic_and_bounded_planning():
    w = build_seed(0)
    table, costs, scored_cols, probe_cols = _tableau(w)
    orc = scoring.oracle(w)
    greedy = _greedy_myopic(table, costs, scored_cols, probe_cols, w.budget)
    look2 = _lookahead(table, costs, scored_cols, probe_cols, w.budget, 2)
    assert greedy == scoring.floor(w) == 4.0      # myopic play earns only the bait (the floor)
    assert look2 == 8.0                            # a 2-step planner mines the shallow vein, not the deep prospect
    assert orc == 10.0 and orc > look2 > greedy    # the gap needs depth-3, position-reading play


# --------------------------------------------------------------------------- the dead end is real
def test_barren_prospect_payoff_is_never_pinnable():
    """The graded seam's payoff mirrors an UNPROBEABLE noise register (reg 9) when barren, so no
    probe sequence can pin it -- a genuine dead end the assay tells you to turn around on. Proof:
    two barren worlds differing ONLY in the noise register are indistinguishable to every probe yet
    disagree on the barren payoff, so a player can never force its value."""
    w = build_seed(0)
    h0 = [0] * w.R                                  # assay reg 5 == 0 -> barren
    h1 = list(h0); h1[9] = 1                        # flip only the unprobeable noise register
    h0, h1 = tuple(h0), tuple(h1)
    for p in w.positions():
        if w.probeable(p):
            assert w.observe(p, h0) == w.observe(p, h1)   # no probe can tell the two worlds apart
    assert any(w.observe(("pay", 1, p), h0) != w.observe(("pay", 1, p), h1) for p in range(8))


# --------------------------------------------------------------------------- score_run on the seed world
def _col(w, descriptor):
    return list(w.positions()).index(descriptor)


def test_lazy_bait_only_run_scores_zero():
    """Grabbing the four bait cells and submitting them (the lazy floor) normalises to 0."""
    w = build_seed(0)
    obs = [(_col(w, ("clear", ci, p)), w.reveal(("clear", ci, p))) for ci in (0, 1) for p in (0, 1)]
    sub = {_col(w, ("clear", ci, p)): w.reveal(("clear", ci, p)) for ci in (0, 1) for p in (0, 1)}
    assert scoring.score_run(w, {"observations": obs, "submission": sub}) == 0.0


def test_mining_the_vein_scores_above_floor():
    """Read the vein's pointer (which ore is live) then that ore, and submit its 4 payoff cells:
    pure inference, above the floor. Also checks the ungameable guarantee -- a guess at an
    un-probed prospect payoff cell earns nothing."""
    w = build_seed(0)
    obs = [(_col(w, ("pointer", 0)), w.reveal(("pointer", 0)))]
    live_ore_j = w.reveal(("pointer", 0)) % 2
    obs.append((_col(w, ("ore", 0, live_ore_j)), w.reveal(("ore", 0, live_ore_j))))
    bait = [(_col(w, ("clear", ci, p)), w.reveal(("clear", ci, p))) for ci in (0, 1) for p in (0, 1)]
    obs += bait
    sub = {_col(w, ("pay", 0, p)): w.reveal(("pay", 0, p)) for p in range(4)}
    sub.update({c: v for c, v in bait})
    # honest: bait (4) + vein (4) pinned = raw 8 -> (8-4)/(10-4)
    honest = scoring.score_run(w, {"observations": obs, "submission": dict(sub)})
    assert honest == pytest.approx((8 - 4) / (10 - 4))
    # cheat: also submit an un-probed, un-pinned prospect payoff cell -> must not change the score
    sub[_col(w, ("pay", 1, 0))] = w.reveal(("pay", 1, 0))
    assert scoring.score_run(w, {"observations": obs, "submission": sub}) == honest


def test_full_feasible_sharp_run_reaches_one():
    """A budget-feasible oracle-style run in a RICH-prospect draw (assay, pointer, ore for both the
    prospect and the vein = 5 probes) pins 12 cells, at/above the oracle -> normalises to 1.0."""
    w = next(build_seed(s) for s in range(50) if build_seed(s).reveal(("assay", 1)) != 0)
    obs, sub = [], {}
    # prospect (rich): assay, pointer, live ore -> its 8 payoff cells
    obs.append((_col(w, ("assay", 1)), w.reveal(("assay", 1))))
    obs.append((_col(w, ("pointer", 1)), w.reveal(("pointer", 1))))
    pj = w.reveal(("pointer", 1)) % 2
    obs.append((_col(w, ("ore", 1, pj)), w.reveal(("ore", 1, pj))))
    sub.update({_col(w, ("pay", 1, p)): w.reveal(("pay", 1, p)) for p in range(8)})
    # vein: pointer, live ore -> its 4 payoff cells
    obs.append((_col(w, ("pointer", 0)), w.reveal(("pointer", 0))))
    vj = w.reveal(("pointer", 0)) % 2
    obs.append((_col(w, ("ore", 0, vj)), w.reveal(("ore", 0, vj))))
    sub.update({_col(w, ("pay", 0, p)): w.reveal(("pay", 0, p)) for p in range(4)})
    assert scoring.score_run(w, {"observations": obs, "submission": sub}) == 1.0


# --------------------------------------------------------------------------- the model-free invariant
def test_world_package_is_model_free():
    """The integrity floor: nothing under hta/world/ imports hta.llm (enforced, not just intended).
    Checks import statements, not prose -- the docstrings name the rule on purpose."""
    root = Path(wspec.__file__).parent
    for py in root.rglob("*.py"):
        for line in py.read_text().splitlines():
            s = line.strip()
            assert not (s.startswith(("import hta.llm", "from hta.llm"))
                        or s.replace(" ", "").startswith("fromhtaimportllm")), \
                f"{py} must not import hta.llm"
