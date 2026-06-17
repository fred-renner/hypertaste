"""The world -- the content. The planted game(s) the player faces.

This package holds *what a world is made of* and the hand-authored seed world. It is the
mutable, family-specific half: when the smith proposes richer parts, `spec.py` changes;
the grader in `hta/lab/` does not.

Two integrity invariants live here as boundaries, not just intentions:
  - Nothing under `hta/world/` imports `hta.llm` -- the content is model-free, like the grader.
  - Safe-eval: a world arrives as a *validated declarative spec* (data) and is expanded by
    `build`. Model output is never imported or executed. See `spec.py` and DESIGN.md.

Evolved worlds live in the archive; only the seed world is checked in here (under `seed/`),
the mirror of the seed playbook under `hta/dgmh/seed/`.
"""
