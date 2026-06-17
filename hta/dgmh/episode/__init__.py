"""LOOP 1's innermost step — the task agent's play (a single episode) and the airgap.

The play runs the task agent through the confined probe tools; per the integrity floor it reaches
the world only through those tools, never by importing the hidden values. `state.py` is the pure
world-state machine + the band judge; `server.py` is the stdio-MCP wrapper (the airgap). See
DESIGN.md / README ("The three planes").
"""

from .state import (EpisodeState, canonical_spec, draw_hstar, normalize, spec_from_dict,
                    spec_to_dict, state_from_env, state_to_env)

__all__ = ["EpisodeState", "canonical_spec", "draw_hstar", "normalize", "spec_from_dict",
           "spec_to_dict", "state_from_env", "state_to_env"]
