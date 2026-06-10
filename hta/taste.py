"""TASTE plane: the Solomonoff/MDL generality prior on the agent PROGRAM.

The only term that survived the reset's "no taste prior in the score" rule: a
description-length prior applied at SELECTION time (not in the world-score the agent is
optimized against), so among comparable fitness the shorter program -- the one that
captured a real regularity rather than the curriculum -- wins. See hta/archive.py.
"""

import ast
from typing import Optional


def program_description_length(source: str) -> Optional[int]:
    """A dumb, robust description-length proxy for the agent PROGRAM -- the Solomonoff/MDL
    prior, measured so it stays ungameable. It counts AST nodes + the character length of
    string/constant literals (so logic hidden in a long prompt string is not free), and
    ignores comments and whitespace (you can't pad your way shorter, or pay for blank
    lines). Returns None if the source doesn't parse -- an invalid program is not selected
    anyway. This is the only place 'Occam' enters the system, and it enters as a prior on
    the *program*, never as a term in the score the agent is optimized against."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    size = 0
    for node in ast.walk(tree):
        size += 1
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            size += len(node.value)
    return size
