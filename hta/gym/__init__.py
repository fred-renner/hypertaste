"""LOOP 2 -- grow the WORLDS (the world-smith; the curriculum).

The second co-evolution loop. When the player saturates the current worlds, the smith invents a
harder one -- it proposes world *structure* (a declarative spec), never the score -- and the
ship-gate admits it only if the lab grades it hard AND solvable AND just past the champion's
reach (the ZPD). The smith borrows the lab's grader (`grade_world`) to dial difficulty: same
scorer that grades a player's run, pointed at a world.

  - smith.py      -- the inventor: propose a spec from the diet (parts box, catalogue, where the
                     champion loses points), never the prior world's full wiring or the score.
  - ship_gate.py  -- realize via the lab -> hard + solvable + ZPD. Model-free, deterministic.
  - loop.py       -- the curriculum: at saturation, smith -> gate -> hand to LOOP 1 -> graduate.
  - wish.py       -- the wish channel (write-only; new-part proposals for the human).
  - catalogue.md  -- the taste-habit catalogue (the smith's reading list only).

STATUS: DRAWN, STUBBED. Built after LOOP 1 climbs on the seed world (DESIGN.md, Chapter 2:
prove the inner loop first). The reference is hta/_trail/world_smith.py + worlds.py.
"""
