"""What a world is made of: the spec format, its validator, and the build step.

The smith writes a *spec* -- a declarative description of a world in the box of legal parts
(the part types + the rules for wiring them). This module says what a legal spec looks like
(`validate`) and turns a validated one into a playable world (`build`). It is the safe-eval
seam: data in, world out, never code -- a spec is never imported or executed, only read by
the expander.

`build` returns something implementing `hta.lab.scoring.World` (the questions the grader
asks). The spec/part vocabulary is family-specific and lives here in `world/`; the grader
that rides the World shape is generic and lives in `lab/`. That split is deliberate: a
richer part box changes this file, not the grader.

Stub: the part types and the expander land when the seed world is authored (informed by the
worked example in hta/_trail/worlds.py). This module is model-free -- it must never import
hta.llm.
"""

from __future__ import annotations

from typing import Mapping

from hta.lab.scoring import World


def validate(spec: Mapping) -> None:
    """Check a proposed spec uses only legal parts, wired legally. Raise on a bad spec.

    The safety is everything the part box cannot say: a spec that fails here is never built.
    """
    raise NotImplementedError("part types + wiring rules land with the seed world")


def build(spec: Mapping, *, seed: int) -> World:
    """Expand a validated spec into a playable world, drawing its hidden answer from `seed`.

    The returned world answers the grader's questions (positions / cost / value). The hidden
    answer it carries is held only harness-side; it never reaches a player's tool surface.
    """
    raise NotImplementedError("the deterministic expander lands with the seed world")
