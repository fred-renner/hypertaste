"""The wish channel -- write-only proposals for new world parts.

When the smith wants a part the box cannot yet express, it writes a *wish*: inert text,
surfaced only to the human for ratification. New parts are code, and code enters the world
language through a human, never by self-ratification (safe-eval, one level up).

INVARIANT (write-only): a wish is never read back by the loop or any agent. Nothing that feeds
a model prompt may import this module. Wishes flow one way -- out to the human-facing lineage
report -- and never circle back to bias selection.

STATUS: stubbed -- built after LOOP 1 climbs. Reference: the wish surface in DESIGN.md (the
integrity floor) -- it has no code analogue in `_trail/` yet.
"""
