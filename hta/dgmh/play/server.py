"""The confined tool surface -- the airgap on the play side.

A stdio-MCP server exposing one play's primitives (a thin wrapper over PlayState) as the ONLY
channel between the player (the model session) and the world. The player has no filesystem,
Bash, or web tools; it speaks JSON-RPC over stdio and nothing else. Tool confinement IS the
airgap: the hidden answer lives in this process's state, never on a tool result.

Roles are gated by toolset (the reference: a top session gets the full orchestration allowlist;
a spawned worker is confined to probe/remaining) -- see Config.top_allowed_tools /
worker_allowed_tools.

Stub: the MCP framing + dispatch land when LOOP 1 is wired (reference:
hta/_trail/probe_server.py).
"""

from __future__ import annotations


def serve() -> None:
    """Run the stdio-MCP loop for one play, dispatching the player's tool calls to PlayState."""
    raise NotImplementedError("the confined tool surface lands when LOOP 1 is wired")
