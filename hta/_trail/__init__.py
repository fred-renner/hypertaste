"""Chapter 2 (the investigation-map), post-reset — see RESET_DESIGN.md.

`anchor.py` realizes the **anchor trail world**: follow a trail of pointers through a
too-large hypothesis space to a buried landmark while fat "clearing" claims pay you for going
the wrong way. It is pure **allocation** under a scarce probe budget (every cell is a lookup, so
it cannot compile into a solver), with an exact belief-MDP **coverage oracle by simulation** and
a model-free floor->oracle band. `run_anchor.py` build-screens it (oracle >> heuristic).

The reseed (RESET_DESIGN.md -> "Next actions" 3, DONE) added the frozen substrate around it:
`episode_state.py` (the world-state machine + band judge), `probe_server.py` (the confined
probe-MCP server with the seven primitives + spawn), `loop.py` (the model-orchestrated DGM-H loop),
and the only evolvable node, `seed/playbook.md` (non-executable English). Next is live calibration
(action 4): land Haiku in-band on the anchor family.
"""
