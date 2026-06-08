"""Chapter 2 (the investigation-map), post-reset — see RESET_DESIGN.md.

`anchor.py` realizes the **anchor trail world**: follow a trail of pointers through a
too-large hypothesis space to a buried landmark while fat "clearing" claims pay you for going
the wrong way. It is pure **allocation** under a scarce probe budget (every cell is a lookup, so
it cannot compile into a solver), with an exact belief-MDP **coverage oracle by simulation** and
a model-free floor->oracle band. `run_anchor.py` build-screens it (oracle >> heuristic).

The reseed (RESET_DESIGN.md -> "Next actions") adds the confined probe-MCP server, the
model-orchestrated loop, and the only evolvable node, `playbook.md` (non-executable English).
"""
