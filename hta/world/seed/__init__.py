"""The hand-authored seed world -- the smith's worked example (DESIGN.md sec.7), the mirror of the
seed playbook under hta/dgmh/seed/. One disposable *instance* of a spec family in hta/world/spec.py.
"""

from hta.world.seed.prospect import build_seed, seed_spec

__all__ = ["seed_spec", "build_seed"]
