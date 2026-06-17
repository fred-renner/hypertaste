"""The world-smith -- the inventor. Propose world STRUCTURE, never the score.

The smith writes a declarative spec for a harder world, reading only its diet: the parts box,
the taste-habit catalogue, and where the champion is losing points -- never the prior world's
full wiring (anchoring is from what's in front, not history) and never the grader. Its output is
data, validated by hta.world.spec.validate before anything is built (safe-eval).

STATUS: stubbed -- built after LOOP 1 climbs. Reference: `propose_move` / `realize_proposal`
in hta/_trail/world_smith.py.
"""
