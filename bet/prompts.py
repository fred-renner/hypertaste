"""Prompts for the two arms.

The split is the whole experiment design (BET.md): the *harness* is fixed and
identical across arms, and the only thing toggled is the *decision discipline*.

  * KICKOFF  -- the fixed harness: how to drive the world through `dw`, the
                act/observe loop, the budget. Goes in the `-p` (user) turn,
                identical for both arms.
  * arm prose (playbook.md / baseline.md) -- how to *choose* the next move.
                Goes in --append-system-prompt. This is the single toggle.

Neither names the world or the task family -- the discipline must be world-
general or it is measuring overfitting, not taste.
"""

import os

_HERE = os.path.dirname(os.path.abspath(__file__))

KICKOFF = """\
You are dropped into an interactive world and must complete a task by taking \
actions, one at a time. You discover the task and your surroundings by looking.

You act ONLY through a command-line tool, `dw`, run with Bash:

  python dw.py observe     -> your current situation, INCLUDING your task
  python dw.py actions     -> the kinds of moves you can make (and their args)
  python dw.py locations   -> named places you can teleport to
  python dw.py act '<json>'-> make one move; prints the result and your new view

Object arguments (arg1/arg2) are the integer UUIDs shown by `observe`. Examples:
  python dw.py act '{"action":"TELEPORT_TO_LOCATION","arg1":"Instrument Table"}'
  python dw.py act '{"action":"READ","arg1":12345}'
  python dw.py act '{"action":"USE","arg1":12345,"arg2":67890}'
If a move puts you in a dialog, reply with:
  python dw.py act '{"chosen_dialog_option_int": 2}'

Each `act` advances the world one step and spends one unit of your move budget.
The world pushes back: read each result, because it tells you whether your idea
was right. Keep choosing and making moves until the task is complete or the
budget reaches zero.

Start now: run `python dw.py observe` to read your task and look around, then \
`python dw.py actions` and `python dw.py locations` once to learn your options. \
Think briefly about your next move, then make it. Continue move by move."""


def load_arm(arm: str) -> str:
    """Return the system-prompt prose for an arm: 'on' (playbook) or 'off'
    (baseline)."""
    fname = {"on": "playbook.md", "off": "baseline.md"}.get(arm)
    if not fname:
        raise ValueError(f"unknown arm {arm!r}; expected 'on' or 'off'")
    with open(os.path.join(_HERE, fname), encoding="utf-8") as f:
        return f.read()
