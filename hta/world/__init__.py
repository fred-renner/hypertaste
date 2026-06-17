"""What a world IS: the agent-inaccessible scorer + hidden state + the mechanical oracle (DESIGN.md).

This package is the world plane (the three-plane picture, README). It holds:
  * `language.py` — the WORLD LANGUAGE: the part-box (Clearing/Chain/Fork) + WorldSpec + validate +
    the deterministic expander. The smith composes worlds out of these parts.
  * `grade.py`    — the world-agnostic grading engine: the dumb coverage scorer, the no-inference
    floor, the belief-MDP oracle, and the model-free build-screen. The integrity floor's math.
  * `contract.py` — the World interface the engine consumes + the band/score/realize facade.
  * `instances.py`— named worlds authored as parts-lists (instance0 is the worked example).

Nothing in `hta.dgmh.episode` may import the hidden values from here — the airgap is this folder
line. The player reaches the world only through the confined probe tools (hta/dgmh/episode).
"""

from .contract import World, band, realize, score
from .grade import (BASKET, clairvoyant_value, coverage_earned, determined, floor_value,
                    lookahead_value, normalize, observed_belief, oracle_value, score_submission,
                    screen, simulate)
from .instances import (canonical_spec, draw_hstar, instance0, ladder_world, single_chain_world)
from .language import (Chain, Clearing, Fork, Region, WorldSpec, build_tableau, public_cells,
                       validate)

__all__ = [
    "Chain", "Clearing", "Fork", "Region", "WorldSpec", "build_tableau", "public_cells", "validate",
    "World", "band", "realize", "score", "BASKET", "clairvoyant_value", "coverage_earned",
    "determined", "floor_value", "lookahead_value", "normalize", "observed_belief", "oracle_value",
    "score_submission", "screen", "simulate", "canonical_spec", "draw_hstar", "instance0",
    "ladder_world", "single_chain_world",
]
