"""Register-world live-path tests — the model-free machinery only (deterministic, no API cost).

The live episode itself (real_solve) needs Haiku and is exercised by `run_calibration.py
--backend real`; here we lock the pieces that bracket it: realizing a LinkSpec into cells, the
floor->oracle references, normalization, and scoring. These are the integrity floor for the
calibration — if they drift, a 'calibrated' verdict means nothing.
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta.ch2 import register_world as rw  # noqa: E402
from hta.ch2 import threshold  # noqa: E402
from hta.ch2.threshold import LinkSpec  # noqa: E402

TRAP = LinkSpec("trap-tri", R=4, K=3, Ld=2, Ll=2,
                edges=((1, 2), (1, 3), (2, 3)), budget=3, direct=(0,))


def test_realize_is_seeded_bounded_and_consistent():
    regs, cells = rw.realize(TRAP, random.Random(0))
    assert len(cells) == TRAP.M
    assert all(0 <= v < TRAP.K for v in cells)
    assert all(0 <= r < TRAP.K for r in regs)
    # same seed -> same world (reproducible episodes)
    assert rw.realize(TRAP, random.Random(0))[1] == cells
    # the realized cells are exactly the tableau row for the drawn registers
    table, _ = threshold.build_tableau(TRAP)
    hyps = list(__import__("itertools").product(range(TRAP.K), repeat=TRAP.R))
    assert list(table[hyps.index(regs)]) == cells


def test_references_match_threshold_and_order():
    ref = rw.references(TRAP)
    # the determined values come straight from the threshold module (single source of truth)
    assert ref["floor_det"] == threshold.floor_value(TRAP)
    assert ref["oracle_det"] == threshold.oracle_value(TRAP)
    assert ref["floor_det"] == 3 and ref["oracle_det"] == 6 and ref["best_heur_det"] == 5
    # raw coverage preserves the ordering floor <= best heuristic <= oracle
    assert ref["floor_raw"] <= ref["best_heur_raw"] <= ref["oracle_raw"]


def test_normalize_anchors_the_band():
    ref = rw.references(TRAP)
    assert abs(rw.normalize(ref["floor_raw"], ref) - 0.0) < 1e-9   # floor -> 0
    assert abs(rw.normalize(ref["oracle_raw"], ref) - 1.0) < 1e-9  # oracle -> 1
    assert rw.normalize(0.0, ref) == 0.0 and rw.normalize(1.0, ref) == 1.0  # clamped


def test_score_perfect_and_partial():
    ref = rw.references(TRAP)
    _, cells = rw.realize(TRAP, random.Random(7))
    perfect = rw.score(cells, cells, ref)
    assert perfect["raw"] == 1.0 and perfect["correct"] == TRAP.M and perfect["valid"]
    # a no-inference walker (mock) nails the probed cells and stays well below the articulable
    # ceiling — it does no inference, so it cannot approach the heuristic/oracle band. (A single
    # realized world can wobble a little above the *expected* floor on guess-luck, so we bound it
    # against the best-heuristic position, not the floor.)
    recon = rw.mock_solve(TRAP, cells)
    s = rw.score(cells, recon, ref)
    assert s["valid"] and len(recon) == TRAP.M
    assert s["correct"] >= TRAP.budget
    assert s["norm"] < rw.normalize(ref["best_heur_raw"], ref)  # below the closed-form ceiling
    # invalid (wrong length) submission is flagged
    assert not rw.score(cells, [0, 0], ref)["valid"]


def test_prompt_is_public_map_without_the_seed():
    regs, _ = rw.realize(TRAP, random.Random(3))
    prompt = rw.build_prompt(TRAP)
    # the public world map is present: every cell and the register symbols
    assert f"cell {TRAP.M - 1}:" in prompt and "cell 0:" in prompt
    assert "r0" in prompt and f"r{TRAP.R - 1}" in prompt
    assert str(TRAP.budget) in prompt
    # it must NOT leak the hidden seed: the drawn register tuple never appears verbatim
    assert str(list(regs)) not in prompt and str(regs) not in prompt
