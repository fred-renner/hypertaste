"""LOOP 1 -- grow the PLAYER (the DGM-H inner loop).

A task agent plays a hidden world through confined probe tools (one *play* = one attempt);
the lab scores the run; a meta-agent rewrites the player's playbook -- non-executable English
-- from a *sanitized* conduct report. Over iterations the playbook accumulates taste.

What lives here:
  - archive.py  -- (real) open-ended stepping-stones + parent selection + the length prior.
                   The world-agnostic store; destined for the shared `hta/archive/` once
                   `_trail/` retires.
  - sandbox.py  -- (real) the meta-agent's world airgap (Direct | Docker).
  - play/       -- one attempt: the world-state machine + the confined tool surface.
  - report.py   -- builds the sanitized conduct report (the meta-side airgap wall).
  - measure.py  -- the read-only instruments that prove taste is climbing (selection-blind).
  - meta.py     -- the meta-edit (rewrite the playbook via the sandbox).
  - loop.py     -- the iteration: select parent -> eval -> meta-edit -> eval child -> archive.

See DESIGN.md (the two loops, the integrity floor) and CLAUDE.md.
"""
