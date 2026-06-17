"""The lab -- the grader. One machine, used two ways.

The lab scores a player's *run* (how well it did) and rates a *world's* difficulty
(how hard it is), with the same two reference points: best-possible play and lazy play.
For a run, it places the player's result between them; for a world, it measures the gap
between best and lazy itself (wide gap => skill matters; reachable top => solvable).

LOOP 1's play calls `score_run`; LOOP 2's smith calls `grade_world`. Same scorer, two
questions -- that is why this is one package, not two.

INVARIANT (enforced by the import graph): nothing under `hta/lab/` imports `hta.llm`.
The grader is model-free *by construction* -- a module that cannot call a model cannot
be gamed by one. The lab is also agent-inaccessible: its source never reaches a player
or the meta-agent. See DESIGN.md (the integrity floor) and CLAUDE.md.
"""
