"""hypertaste: a self-improving research-taste harness (DGM-H pipeline).

The tree is cut around the system's loops (see DESIGN.md):
  * hta.world  -- what a world IS: the agent-inaccessible scorer + hidden state + oracle.
  * hta.dgmh   -- LOOP 1, grow the AGENT: the episode (the play), the archive + the
                  program-length prior, the meta-agent airgap (sandbox), the loop.
  * hta.gym    -- LOOP 2, grow the WORLD: the world-smith (propose + gate the curriculum).
  * hta._trail -- the retired trail puzzle, quarantined as a temporary test world.

Shared plumbing sits at the top: hta.llm (the claude -p seam; all model calls funnel here)
and hta.config (model assignment, budgets, paths).
"""

__version__ = "0.1.0"
