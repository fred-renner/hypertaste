"""LOOP 2 -- grow the WORLD (the curriculum; ZPD targeting).

The second co-evolution loop (the world-smith, `smith.py`): propose the next world's STRUCTURE as a
validated parts-list in the world language, then gate it -- hard AND solvable AND just past the
champion's reach -- to keep the agent in its zone of proximal development. The referee and the
perfect-play oracle are re-derived mechanically from the structure, never authored (the integrity
wall, one level up). See DESIGN.md §5-7.
"""

from .smith import (CURRICULUM, INVENTOR_INSTRUCTION, commit_deepest, demonstrate, propose_move,
                    realize_proposal, run_curriculum, scout_ladder_then_commit, scout_then_commit,
                    ship_gate)

__all__ = ["CURRICULUM", "INVENTOR_INSTRUCTION", "commit_deepest", "demonstrate", "propose_move",
           "realize_proposal", "run_curriculum", "scout_ladder_then_commit", "scout_then_commit",
           "ship_gate"]
