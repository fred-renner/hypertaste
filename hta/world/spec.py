"""What a world is made of: the spec format, its validator, and the build step.

The smith writes a *spec* -- a declarative description of a world in the box of legal parts
(the part types + the rules for wiring them). This module says what a legal spec looks like
(`validate`) and turns a validated one into a playable world (`build`). It is the safe-eval
seam: data in, world out, never code -- a spec is never imported or executed, only read by
the expander.

`build` returns something implementing `hta.lab.scoring.World` (the questions the grader
asks: the hidden-answer set, the positions, their cost, the value law `observe`, and which
positions are probeable / scored). The spec/part vocabulary is family-specific and lives here
in `world/`; the grader that rides the World shape is generic and lives in `lab/`. That split
is deliberate -- and the value law lives in `observe` here, never in the grader -- so a richer
part box changes this file, not the grader.

This module is model-free -- it must never import hta.llm.

----------------------------------------------------------------------------------------------
The "prospect" family -- the seed world's part box (see hta/world/seed/prospect.py)
----------------------------------------------------------------------------------------------
A prospect world is `R` hidden registers (each in 0..K-1; the hidden answer is one of the K**R
assignments) wired into three kinds of part. The split is what makes the floor->oracle gap *be
taste* -- position-reading, not a fixed formula -- rather than a single repeated tactic (the
instance-0 / trail collapse; see findings/2026-06-14 and the grader's own note in scoring.py):

  * clearing  -- a register that pays a block of `cells` scored cells you can ALSO probe
                 (probeable + scored). One probe pins the whole block. The immediate-payoff
                 BAIT: a lazy player grabs these (they set the floor), a greedy player over-
                 invests in them, and that is the deception that the deep seams punish.

  * seam      -- a deep INFERENCE vein. Its `cells` scored payoff cells are NOT probeable; you
                 reconstruct them. The value law: a `pointer` register selects which register of
                 the `ore` pool is LIVE (ore[pointer-value mod len]); the payoff mirrors that
                 live ore. So pinning the payoff needs the pointer pinned (which ore) AND that
                 ore pinned (its value) -- a depth-2 walk that pays ZERO coverage until the ore
                 lands. *Which* ore is live is fresh every episode (the hidden pointer value), so
                 there is no memorisable answer: you read the position to choose the probe.

  * prospect  -- a seam with a hidden GRADE (a dead end you must discover). An `assay` register
                 (cheap, pays nothing) reads rich/barren: rich (assay-value != 0) -> the payoff
                 mirrors the live ore as above; barren (assay-value == 0) -> the payoff mirrors a
                 `noise` register that has NO instrument, so it can NEVER be pinned. The tasteful
                 move is to assay first and turn around on a barren vein instead of sinking the
                 (deeper, depth-3: assay->pointer->ore) shaft into it. A graded seam is the
                 boredom / learning-gradient habit (DESIGN sec.2, sec.4) the trail lacked.

Register roles partition {0..R-1} one-to-one (each register has exactly one job), so the
hypothesis space stays minimal and the exact oracle stays computable (an invariant, scoring.py).
A spec is plain JSON-able data; `validate` is the integrity wall in code -- a proposal is built
only if it is a legal structure, never because it claims a score.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from itertools import product
from typing import List, Mapping, Optional, Sequence, Tuple

from hta.lab.scoring import World


# ---------------------------------------------------------------------------
# Parsed parts (the internal, validated form `build` expands -- not the wire spec).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _Clearing:
    reg: int
    cells: int
    cost: int


@dataclass(frozen=True)
class _Seam:
    pointer: int
    ore: Tuple[int, ...]
    cells: int
    assay: Optional[int]            # graded (a possible dead end) iff set
    noise: Optional[int]           # the unprobeable barren target; present iff `assay` is
    cost_assay: int
    cost_pointer: int
    cost_ore: int

    @property
    def graded(self) -> bool:
        return self.assay is not None


# ---------------------------------------------------------------------------
# validate -- the safe-eval gate. Raises on a bad spec; returns None on a legal one.
# ---------------------------------------------------------------------------
def validate(spec: Mapping) -> None:
    """Check a proposed spec uses only legal parts, wired legally. Raise ValueError on a bad spec.

    The safety is everything the part box cannot say: a spec that fails here is never built. All
    problems are collected and raised together so an author sees the full list, not just the first.
    """
    issues: List[str] = []

    def _int(v, name) -> Optional[int]:
        if isinstance(v, bool) or not isinstance(v, int):
            issues.append(f"{name} must be an int, got {v!r}")
            return None
        return v

    if not isinstance(spec, Mapping):
        raise ValueError(f"spec must be a mapping, got {type(spec).__name__}")
    if spec.get("kind") != "prospect":
        issues.append(f"kind must be 'prospect', got {spec.get('kind')!r}")

    K = _int(spec.get("K"), "K")
    R = _int(spec.get("R"), "R")
    budget = _int(spec.get("budget"), "budget")
    if K is not None and K < 2:
        issues.append("K must be >= 2")
    if R is not None and R < 2:
        issues.append("R must be >= 2")
    if budget is not None and budget < 1:
        issues.append("budget must be >= 1")

    used: List[int] = []          # every referenced register, in declaration order
    in_range = (lambda r: R is not None and isinstance(r, int) and not isinstance(r, bool)
                and 0 <= r < R)

    clearings = spec.get("clearings", [])
    if not isinstance(clearings, Sequence) or isinstance(clearings, (str, bytes)):
        issues.append("clearings must be a list")
        clearings = []
    for i, c in enumerate(clearings):
        if not isinstance(c, Mapping):
            issues.append(f"clearing {i} must be a mapping"); continue
        r = c.get("reg")
        if not in_range(r):
            issues.append(f"clearing {i} reg {r!r} out of range [0,{R})")
        else:
            used.append(r)
        if not isinstance(c.get("cells"), int) or isinstance(c.get("cells"), bool) or c["cells"] < 1:
            issues.append(f"clearing {i} cells must be an int >= 1")
        if "cost" in c and (not isinstance(c["cost"], int) or isinstance(c["cost"], bool) or c["cost"] < 1):
            issues.append(f"clearing {i} cost must be an int >= 1")

    seams = spec.get("seams", [])
    if not isinstance(seams, Sequence) or isinstance(seams, (str, bytes)):
        issues.append("seams must be a list")
        seams = []
    if len(seams) < 1:
        issues.append("need at least one seam (a world must have a deep inference vein)")
    for i, s in enumerate(seams):
        if not isinstance(s, Mapping):
            issues.append(f"seam {i} must be a mapping"); continue
        p = s.get("pointer")
        if not in_range(p):
            issues.append(f"seam {i} pointer {p!r} out of range [0,{R})")
        else:
            used.append(p)
        ore = s.get("ore")
        if not isinstance(ore, Sequence) or isinstance(ore, (str, bytes)) or len(ore) < 1:
            issues.append(f"seam {i} ore must be a non-empty list of registers")
        else:
            for r in ore:
                if not in_range(r):
                    issues.append(f"seam {i} ore reg {r!r} out of range [0,{R})")
                else:
                    used.append(r)
        if not isinstance(s.get("cells"), int) or isinstance(s.get("cells"), bool) or s["cells"] < 1:
            issues.append(f"seam {i} cells must be an int >= 1")
        assay, noise = s.get("assay"), s.get("noise")
        if (assay is None) != (noise is None):
            issues.append(f"seam {i} assay and noise must be set together (a graded seam needs a "
                          f"barren target) or both omitted (an always-rich vein)")
        if assay is not None:
            if not in_range(assay):
                issues.append(f"seam {i} assay {assay!r} out of range [0,{R})")
            else:
                used.append(assay)
            if not in_range(noise):
                issues.append(f"seam {i} noise {noise!r} out of range [0,{R})")
            else:
                used.append(noise)
        for k in ("cost_assay", "cost_pointer", "cost_ore"):
            if k in s and (not isinstance(s[k], int) or isinstance(s[k], bool) or s[k] < 1):
                issues.append(f"seam {i} {k} must be an int >= 1")

    # The register roles must partition {0..R-1} one-to-one: no reuse, no orphans, no gaps.
    if R is not None and not issues:
        if len(used) != len(set(used)):
            dup = sorted({r for r in used if used.count(r) > 1})
            issues.append(f"registers reused across roles: {dup} (each register has exactly one job)")
        if set(used) != set(range(R)):
            missing = sorted(set(range(R)) - set(used))
            extra = sorted(set(used) - set(range(R)))
            if missing:
                issues.append(f"orphan registers (declared in R but unused): {missing}")
            if extra:
                issues.append(f"registers out of [0,{R}): {extra}")

    if issues:
        raise ValueError("invalid prospect spec: " + "; ".join(issues))


# ---------------------------------------------------------------------------
# The built world -- a validated spec expanded into the World the grader reads.
# ---------------------------------------------------------------------------
class _ProspectWorld:
    """A built prospect world. Implements the `hta.lab.scoring.World` protocol: the grader reads
    only `budget` + the six methods and never sees `truth`. Positions are referred to by their
    index in `positions()` order (the `col` a run logs) -- the order below is fixed and stable.

    The drawn hidden answer (`truth`) is held here harness-side only; the play harness reads it via
    `reveal(position)` to answer a probe, and it never reaches a player's tool surface (per the
    integrity floor). The grader ignores it entirely."""

    def __init__(self, K: int, R: int, budget: int,
                 clearings: Sequence[_Clearing], seams: Sequence[_Seam], truth: Tuple[int, ...]):
        self.K = K
        self.R = R
        self.budget = int(budget)
        self.clearings = list(clearings)
        self.seams = list(seams)
        self.truth = truth
        self._positions = self._layout()

    # ---- the fixed position layout (clearings, then instruments, then payoff cells) ----
    def _layout(self) -> Tuple[tuple, ...]:
        pos: List[tuple] = []
        for ci, c in enumerate(self.clearings):
            for p in range(c.cells):
                pos.append(("clear", ci, p))
        for si, s in enumerate(self.seams):
            if s.graded:
                pos.append(("assay", si))
            pos.append(("pointer", si))
            for j in range(len(s.ore)):
                pos.append(("ore", si, j))
        for si, s in enumerate(self.seams):
            for p in range(s.cells):
                pos.append(("pay", si, p))
        return tuple(pos)

    # ---- the World protocol ----
    def hypotheses(self):
        return list(product(range(self.K), repeat=self.R))

    def positions(self):
        return self._positions

    def cost(self, position) -> int:
        tag = position[0]
        if tag == "clear":
            return self.clearings[position[1]].cost
        if tag == "assay":
            return self.seams[position[1]].cost_assay
        if tag == "pointer":
            return self.seams[position[1]].cost_pointer
        if tag == "ore":
            return self.seams[position[1]].cost_ore
        return 1                                      # "pay": not probeable, cost never consumed

    def observe(self, position, h) -> int:
        tag = position[0]
        if tag == "clear":
            _, ci, p = position
            return (h[self.clearings[ci].reg] + p) % self.K
        if tag == "assay":
            return h[self.seams[position[1]].assay]
        if tag == "pointer":
            return h[self.seams[position[1]].pointer]
        if tag == "ore":
            _, si, j = position
            return h[self.seams[si].ore[j]]
        # "pay": the value law -- live ore if rich, the unprobeable noise register if barren.
        _, si, p = position
        s = self.seams[si]
        if s.assay is None or h[s.assay] != 0:
            live = s.ore[h[s.pointer] % len(s.ore)]
        else:
            live = s.noise
        return (h[live] + p) % self.K

    def probeable(self, position) -> bool:
        return position[0] in ("clear", "assay", "pointer", "ore")

    def scored(self, position) -> bool:
        return position[0] in ("clear", "pay")

    # ---- harness-only: what a probe of this position actually returns (uses the hidden truth) ----
    def reveal(self, position) -> int:
        """The real observation a player gets when probing `position` -- `observe` under the drawn
        truth. Harness-side only (the future play/server reads it); never on a player's surface."""
        return self.observe(position, self.truth)


def build(spec: Mapping, *, seed: int) -> World:
    """Expand a validated spec into a playable world, drawing its hidden answer from `seed`.

    The returned world answers the grader's questions (hypotheses / positions / cost / observe /
    probeable / scored). The hidden answer it carries is held only harness-side (`truth`); it never
    reaches a player's tool surface.
    """
    validate(spec)
    K, R = int(spec["K"]), int(spec["R"])
    clearings = [_Clearing(reg=int(c["reg"]), cells=int(c["cells"]), cost=int(c.get("cost", 1)))
                 for c in spec.get("clearings", [])]
    seams = []
    for s in spec["seams"]:
        assay = s.get("assay")
        seams.append(_Seam(
            pointer=int(s["pointer"]),
            ore=tuple(int(r) for r in s["ore"]),
            cells=int(s["cells"]),
            assay=None if assay is None else int(assay),
            noise=None if s.get("noise") is None else int(s["noise"]),
            cost_assay=int(s.get("cost_assay", 1)),
            cost_pointer=int(s.get("cost_pointer", 1)),
            cost_ore=int(s.get("cost_ore", 1))))
    rng = random.Random(seed)
    truth = tuple(rng.randrange(K) for _ in range(R))
    return _ProspectWorld(K, R, int(spec["budget"]), clearings, seams, truth)
