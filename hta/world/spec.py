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

The grammar (first principles, derived from the integrity floor's guardrails -- NOT from the
retired trail's chains/signposts/valleys):

  * **Variables** -- the hidden unknowns. A spec lists `n_vars` variables, each over `K` values,
    so `hypotheses()` is their product (one is the drawn truth).
  * **Readouts** -- the positions. Each is a deterministic lookup of a subset of the variables.
    Three roles, all spelled in the same kit:
      - **immediate** readout (scored, probeable): reveals one variable directly -> pays coverage
        the moment you probe it = greedy bait.
      - **gate** readout (probeable, *unscored*): reveals a prerequisite variable; pays zero
        coverage = a pure feasibility pointer.
      - **gated payoff** (scored, NOT probeable): a block worth `weight` coverage cells whose
        value mirrors a variable *selected by walking a prerequisite path* of gate variables, and
        so is logically pinned ONLY once that whole path is scouted. Committing budget without the
        scout pins none of it -- the compounding-horizon trick, stated as a readout over a
        prerequisite set, with no new part type. A deeper path = a longer horizon, not a new kind.

The path's adaptivity is what forces the scout: each step's hidden value names the next variable
to read (a `hop`, a length-K table mapping the current variable's value -> the next variable), so
no single probe pins the payoff and the path cannot be read off the public structure -- it is
walked one step at a time. ("Chains" are then just one composition of gates, not a primitive.)

This module is model-free -- it must never import hta.llm. Relabeling (a per-episode surface
rename) is deliberately NOT here: `build` stays structure-only so a relabel can sit *above* the
returned World later, in the play surface, never in the expander.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Hashable, Mapping, Sequence, Tuple

from hta.lab.scoring import World


# ---------------------------------------------------------------------------
# The spec is plain data (a dict) -- the safe-eval form: it round-trips through JSON and is read,
# never executed. Shape:
#   {"name": str, "n_vars": int, "K": int, "budget": int,
#    "bait":   [var, ...],                       # immediate readouts (the greedy bait)
#    "payoff": {"start": var,                    # the prerequisite path's first gate variable
#               "hops":  [[var, ...K...], ...],  # each hop: current-var-value -> next variable
#               "weight": int},                  # coverage cells the gated payoff is worth
#    "cost_bait": int, "cost_gate": int}         # costs (optional; default 1)
# Gate readouts are AUTO-DERIVED from the payoff path (every variable the walk can visit gets one),
# so a spec cannot describe an un-scoutable payoff: the parts box keeps itself consistent.
# ---------------------------------------------------------------------------
def to_dict(spec: Mapping) -> dict:
    """Canonicalize a spec to a plain JSON-able dict (lists, not tuples). The safe-eval form: a
    spec is data, surfaced and stored as data, never an object with behavior."""
    p = spec["payoff"]
    return {
        "name": str(spec.get("name", "spec")),
        "n_vars": int(spec["n_vars"]), "K": int(spec["K"]), "budget": int(spec["budget"]),
        "bait": [int(v) for v in spec["bait"]],
        "payoff": {"start": int(p["start"]),
                   "hops": [[int(x) for x in hop] for hop in p["hops"]],
                   "weight": int(p["weight"])},
        "cost_bait": int(spec.get("cost_bait", 1)), "cost_gate": int(spec.get("cost_gate", 1)),
    }


# from_dict is the same canonicalization: a spec has no richer in-memory form than the data itself.
from_dict = to_dict


def path_vars(spec: Mapping) -> Tuple[int, ...]:
    """Every variable the prerequisite walk can visit (the start, then every hop target). These are
    exactly the variables that get a gate readout -- the scoutable prerequisite set."""
    p = spec["payoff"]
    seen = {int(p["start"])}
    for hop in p["hops"]:
        seen.update(int(x) for x in hop)
    return tuple(sorted(seen))


def validate(spec: Mapping) -> None:
    """Check a proposed spec uses only legal parts, wired legally. Raise ValueError on a bad spec.

    The safety is everything the part box cannot say: a spec that fails here is never built. (It is
    *lenient* on difficulty -- a structurally-legal-but-trivial world is the ship-gate's job to
    reject, not the validator's.)
    """
    try:
        n_vars, K, budget = int(spec["n_vars"]), int(spec["K"]), int(spec["budget"])
        bait = [int(v) for v in spec["bait"]]
        p = spec["payoff"]
        start, hops, weight = int(p["start"]), p["hops"], int(p["weight"])
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"malformed spec: {e}")

    rng = range(n_vars)
    if n_vars < 2 or K < 2:
        raise ValueError("need n_vars >= 2 and K >= 2")
    if budget < 1:
        raise ValueError("budget must be >= 1")
    if not bait:
        raise ValueError("empty scored bait set -- need at least one immediate-coverage readout")
    if any(v not in rng for v in bait):
        raise ValueError("bait variable out of range")
    if weight < 1:
        raise ValueError("payoff weight must be >= 1")
    if start not in rng:
        raise ValueError(f"payoff start variable {start} out of range")
    if not hops:
        raise ValueError("gated payoff with no gate -- the path needs >= 1 hop to be earned, "
                         "else the payoff is pinnable by a single probe (not gated)")
    for hi, hop in enumerate(hops):
        if len(hop) != K:
            raise ValueError(f"payoff hop {hi} must have length K={K}")
        if any(int(x) not in rng for x in hop):
            raise ValueError(f"payoff hop {hi} targets a variable out of range")


# ---------------------------------------------------------------------------
# The built world: a fixed list of readout descriptors the grader reads through the World Protocol.
# It carries, as plain attributes the grader never touches, the structural roles (which columns are
# bait, which variable each gate column reads, the payoff path) so the gym's grammar-aware ZPD
# stand-in policies can walk the path. The grader uses ONLY the Protocol methods.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BuiltWorld:
    budget: int
    K: int
    n_vars: int
    _positions: Tuple[tuple, ...]          # descriptors, in fixed order (= the grader's `col` index)
    _cost_bait: int
    _cost_gate: int
    path_start: int
    path_hops: Tuple[Tuple[int, ...], ...]
    # --- structural roles (harness-side only; for the gym's ZPD stand-ins, never the grader) ---
    bait_cols: Tuple[int, ...]
    gate_col: Mapping[int, int]            # variable -> its gate readout's column
    payoff_cols: Tuple[int, ...]
    hstar: Tuple[int, ...] = field(default=())   # the drawn hidden answer (harness-side only)

    # ---- the World Protocol (all the grader ever calls) -- pure dispatch on the descriptor kind ----
    def hypotheses(self) -> Sequence[Hashable]:
        return list(product(range(self.K), repeat=self.n_vars))

    def positions(self) -> Sequence[object]:
        return self._positions

    def cost(self, position: object) -> int:
        return self._cost_bait if position[0] == "bait" else self._cost_gate

    def observe(self, position: object, hypothesis: Hashable) -> int:
        if position[0] in ("bait", "gate"):
            return hypothesis[position[1]]
        # payoff: mirror the variable the prerequisite walk selects under this hypothesis.
        r = self.path_start
        for hop in self.path_hops:
            r = hop[hypothesis[r] % self.K]
        return hypothesis[r]

    def probeable(self, position: object) -> bool:
        return position[0] != "payoff"        # bait + gate probeable; the payoff is inferred only

    def scored(self, position: object) -> bool:
        return position[0] != "gate"          # bait + payoff scored; the gate pays zero coverage


def build(spec: Mapping, *, seed: int = 0) -> BuiltWorld:
    """Expand a validated spec into a playable world, drawing its hidden answer from `seed`.

    Deterministic: same (spec, seed) -> identical world. The hidden answer it carries is held only
    harness-side (`hstar`); it never reaches a player's tool surface. Layout (fixing the `col` index
    the grader and the gym's policies share): bait readouts, then one gate readout per path variable,
    then the `weight`-cell payoff block.
    """
    validate(spec)
    s = to_dict(spec)
    K, n_vars = s["K"], s["n_vars"]
    pvars = path_vars(s)

    positions = []
    bait_cols, gate_col, payoff_cols = [], {}, []

    for v in s["bait"]:                       # immediate readouts: scored + probeable (greedy bait)
        bait_cols.append(len(positions))
        positions.append(("bait", v))

    for v in pvars:                           # gate readouts: probeable, UNSCORED (feasibility pointer)
        gate_col[v] = len(positions)
        positions.append(("gate", v))

    for j in range(s["payoff"]["weight"]):    # gated payoff block: scored, NOT probeable (inferred)
        payoff_cols.append(len(positions))
        positions.append(("payoff", j))

    import random
    rng = random.Random(seed)
    hstar = tuple(rng.randrange(K) for _ in range(n_vars))

    return BuiltWorld(
        budget=s["budget"], K=K, n_vars=n_vars,
        _positions=tuple(positions), _cost_bait=s["cost_bait"], _cost_gate=s["cost_gate"],
        path_start=s["payoff"]["start"],
        path_hops=tuple(tuple(int(x) for x in hop) for hop in s["payoff"]["hops"]),
        bait_cols=tuple(bait_cols), gate_col=dict(gate_col), payoff_cols=tuple(payoff_cols),
        hstar=hstar,
    )
