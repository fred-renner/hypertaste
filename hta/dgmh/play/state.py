"""The per-play world-state machine -- the harness side of one attempt.

Holds the built world (an opaque `hta.lab.scoring.World` handle, with its hidden answer), the
probe budget, the probe log, the scratchpad, and the submission. Exposes the player's primitives
as plain methods (the reference set in the worked example was seven: probe, remaining,
world_map, mem_read, mem_patch, submit_map, spawn). The confined MCP surface in server.py is a
thin wrapper over these.

This module holds hidden state by necessity (it answers probes), but it does NOT import the
grader: per the airgap rule, `hta/dgmh/play/` never imports `hta.lab.scoring`'s oracle/floor/
score -- only the `World` shape it is handed. Grading is harness-side, after the play.

Stub: the state machine + primitives land when LOOP 1 is wired (reference:
hta/_trail/episode_state.py). The world handle comes from hta.world.spec.build.
"""

from __future__ import annotations

from hta.lab.scoring import World


class PlayState:
    """Mutable state for one play. Holds the built world; exposes the player's primitives."""

    def __init__(self, world: World, budget: int) -> None:
        raise NotImplementedError("the world-state machine lands when LOOP 1 is wired")
