"""The World contract — the interface a world implements, and the airgap line.

A *world* (DESIGN.md §2) is the agent-INACCESSIBLE pair of (a) a hidden state realized from a
validated declarative parts-list and (b) a dumb deterministic scorer over it, with a mechanical
perfect-play benchmark. Nothing in `hta.dgmh.episode` may import the hidden values: the player
reaches the world only through the confined probe tools (the airgap), and free Python may compute
only over what was probed. This package (`hta.world`) is that agent-inaccessible side.

The **contract** is the small protocol the world-agnostic grading engine (`grade.py`) consumes. The
one concrete world type — `WorldSpec` (language.py) — implements it, and so will anything the world
language grows into; the oracle/floor/screen never look past these members:

    cells() -> [cell descriptor]          the column layout (probeable/coverage roles fall out)
    cost_of(cell) -> int                  the cost charged to probe a cell
    cell_value(cell, hyp) -> int          the deterministic value law (a LOOKUP, never a solve)
    ramp_curve() -> [float]               the anti-cliff difficulty shape (intrinsic to the parts)
    R, K, budget                          variable pool, colors, the scarce cost budget
    world_map_public(remaining) -> dict   the PUBLIC rules of the game (no hidden values)
    report_blurb() -> str                 a one-line public description (sanitized reports)
    to_dict()/from_dict()                 declarative (de)serialization (safe-eval lifted: data)

The grading engine adds nothing the world can move: `build_tableau` expands the parts, and
`determined`/`floor_value`/`oracle_value`/`screen`/`score_submission` are all `f(structure,
observations)`. That separation — the smith proposes structure, the lab re-derives the score — is
the integrity floor.
"""

from typing import Dict, List, Optional, Protocol, Tuple, runtime_checkable

from . import grade
from .language import WorldSpec, build_tableau


@runtime_checkable
class World(Protocol):
    """The members the grading engine consumes. `WorldSpec` is the concrete implementation."""
    name: str
    R: int
    K: int
    budget: int

    def cells(self) -> List[Tuple]: ...
    def cost_of(self, cell: Tuple) -> int: ...
    def cell_value(self, cell: Tuple, hyp: Tuple[int, ...]) -> int: ...
    def ramp_curve(self) -> List[float]: ...
    def world_map_public(self, remaining: int) -> dict: ...
    def report_blurb(self) -> str: ...
    def to_dict(self) -> dict: ...


def band(spec: WorldSpec) -> Tuple[float, float]:
    """The model-free (floor, oracle) coverage band a world is scored in — spec-constant, cached."""
    return grade.floor_value(spec), grade.oracle_value(spec)


def score(spec: WorldSpec, log: List[dict], submitted: Optional[Dict[int, int]],
          used: int = 0) -> dict:
    """The dumb deterministic judge: band-normalized coverage of the probe LOG + submission. A thin
    re-export of `grade.score_submission` so callers depend on the contract, not the engine."""
    return grade.score_submission(spec, log, submitted, used=used)


def realize(d: dict) -> Tuple[Optional[WorldSpec], List[str]]:
    """Realize a declarative parts-list (the smith's proposal) into a validated world. Returns
    (spec or None, issues). The spec is DATA, never executed (safe-eval lifted): a malformed dict
    yields issues, a well-formed-but-illegal structure yields validation problems."""
    from .language import validate
    try:
        spec = WorldSpec.from_dict(d)
    except (KeyError, TypeError, ValueError) as e:
        return None, [f"malformed structural spec: {e}"]
    issues = validate(spec)
    return (spec if not issues else None), issues
