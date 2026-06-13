"""Instance 0 — the **machine world**, kit v1 (PLAN.md -> "Pass-3 design record v2" §1-§2;
the settled picture in `PASS3_REDO.md`). The first slice of the *world language*: a small box
of part types the lab can assemble into a hidden machine, grade by a dumb deterministic exam, and
QA model-free — never an LLM judge.

The shift from the anchor/trail world (now a regression fixture). There, the score was *coverage*:
cells your probes pinned and you submitted. Here, **only the exam pays, and probing earns nothing**
(PLAN.md §2). You spend a scarce budget driving the machine and reading meters; at the end you
submit a *model* of each output; the lab grades that model on **held-out inputs you did not probe**.
So the score measures **prediction of behaviour you never directly saw** — which is the faithful
shape of research taste: probe to understand, then be tested on what you understood.

What a machine is (kit v1):

  * **inputs** — each output reads one scalar input, an integer in `[0, domain)`. The player sets
    it when probing (full control; nature-driven inputs are a later axis).
  * **components** — the parts. Three types, each a deterministic function of its single parent:
      - `const`  : value = c                       (trivially compressible — one probe)
      - `affine` : value = a*parent + b            (a steady step — extrapolable from a few probes)
      - `lookup` : value = table[parent]           (an arbitrary table — learnable only by enumeration)
  * **outputs** — each output is a short **chain** of components from its input (a lookup, if present,
    is the head so its parent is the input). The chain's *observable law* collapses to one of
    `const` / `affine` / `table`; its **weight** = the chain length = how much hidden machinery sits
    upstream (PLAN.md §2: "weight grows with the machinery upstream"). The weight is **public** (the
    exam says which outputs are worth more); the *kind and parameters are hidden* — discover them by
    probing.

The taste this shapes (planted, never installed — PLAN.md §5): the budget is far smaller than "probe
everything", so a flat smear resolves nothing. The winning move is to **read your position and
concentrate**: spend a few probes to tell an output's kind apart (does the step hold, or did two
points just happen to line up?), fully nail the affordable high-value ones, and **abstain** on the
ones you can't reach — abstaining earns the blind-guess credit, so on an out-of-reach output it is
the *correct* move, scored without a judge. A naive even sweep, and a fit-and-commit prober that
never checks, both score ≈ 0 (the build-screen gate). The gap between them and a tasteful allocation
is the room the inner loop grows into.

Everything here is dumb deterministic `f(structure, choices)` over the realized machine — the
integrity floor. No oracle, no belief-MDP: the baseline is the **best blind guesser** computed from
the answer key (arithmetic), and "is it in the ZPD" is answered by the live loop, never a proxy.
"""

import json
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Lookup values (and so the whole readout alphabet) live in [0, M_VALUES). Kept to single digits so
# a weak student can read and track them; affine outputs are plain integers (no modulus in v1), which
# stay small for the short chains and low coefficients below — and a plain arithmetic step is what
# makes "spot the line" reachable for a weak model (a modular step is a later, harder axis).
M_VALUES = 10
AFFINE_A = (1, 2)        # affine multiplier choices (small -> values stay small, step stays readable)
AFFINE_B = (0, 1, 2, 3)  # affine offset choices


# ---------------------------------------------------------------------------
# Components (the kit) and their evaluation. A component is a small JSON-able dict tagged by `t`.
# ---------------------------------------------------------------------------
def comp_eval(comp: dict, parent: int) -> int:
    t = comp["t"]
    if t == "const":
        return int(comp["c"])
    if t == "affine":
        v = int(comp["a"]) * int(parent) + int(comp["b"])
        m = comp.get("m")
        return v % int(m) if m else v
    if t == "lookup":
        return int(comp["table"][int(parent)])
    raise ValueError(f"unknown component type {t!r}")


def chain_eval(chain: List[dict], x: int) -> int:
    """Compose the chain on an input: input -> c0 -> c1 -> ... -> output."""
    v = x
    for comp in chain:
        v = comp_eval(comp, v)
    return v


def observable_kind(chain: List[dict]) -> str:
    """The law the chain collapses to from outside: a const anywhere fixes the output; otherwise a
    lookup anywhere makes it an arbitrary table; an all-affine chain is itself affine."""
    if any(c["t"] == "const" for c in chain):
        return "const"
    if any(c["t"] == "lookup" for c in chain):
        return "table"
    return "affine"


# ---------------------------------------------------------------------------
# One realized output and the whole machine.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Output:
    """One readout: a chain over an input of size `domain`. `weight` (= chain length, public) is the
    exam value of each of this output's questions; the chain (kind + params) is the hidden seed."""
    domain: int
    weight: int
    chain: Tuple[dict, ...]

    def kind(self) -> str:
        return observable_kind(list(self.chain))

    def f(self, x: int) -> int:
        return chain_eval(list(self.chain), x)

    def answers(self) -> List[int]:
        """The answer key over this output's whole input domain (the exam is the full domain in v1)."""
        return [self.f(x) for x in range(self.domain)]


@dataclass(frozen=True)
class Machine:
    """A realized machine: a list of independent single-input outputs plus the global probe budget.
    The PUBLIC face (`public_map`) shows only domains, weights and the law vocabulary; the chains are
    the hidden seed, reached solely by probing."""
    name: str
    outputs: Tuple[Output, ...]
    budget: int

    # ---- the dumb deterministic exam + scorer (the integrity floor) ----
    def public_map(self, remaining: Optional[int] = None) -> dict:
        """The rules of the game, no hidden values — the generic interface (variable/value, no
        world-story), so the player cannot overfit the container. Each output: its input `domain`
        and its `weight` (points per question). The value law tells the player the hypothesis space
        (const / affine / table) and the scoring contract (only the exam pays; abstain = blind
        credit; a wrong committed value = 0)."""
        return {
            "n_outputs": len(self.outputs),
            "budget": self.budget,
            "remaining": self.budget if remaining is None else int(remaining),
            "outputs": [{"output": i, "domain": o.domain, "weight": o.weight}
                        for i, o in enumerate(self.outputs)],
            "value_law": (
                "Each output reads an integer for the scalar input you set (an integer in "
                "[0, domain)). Each output's law is one of: a constant; an affine map a*input+b "
                "(a steady step you can extrapolate); or an arbitrary lookup table (predictable only "
                "where you have read it). Which law, and its parameters, are HIDDEN — probe to find "
                "out. Higher-weight outputs are worth more per question. You are graded on the FULL "
                "input domain of every output, including inputs you did not probe: a correct law "
                "(affine) or a fully read table earns full weight; abstaining earns a small "
                "blind-guess credit; a committed WRONG value earns zero. Probing spends budget and "
                "earns nothing."),
            "submit_format": ("Map each output index to one of: {\"law\":\"const\",\"c\":int}, "
                              "{\"law\":\"affine\",\"a\":int,\"b\":int}, "
                              "{\"law\":\"table\",\"values\":{\"<input>\":int,...}}, or "
                              "{\"law\":\"abstain\"}. Omitted outputs are treated as abstain."),
        }

    def report_blurb(self) -> str:
        slots = ", ".join(f"o{i}(D{o.domain},w{o.weight})" for i, o in enumerate(self.outputs))
        return (f"{len(self.outputs)} outputs [{slots}]; each is a hidden const/affine/table law of "
                f"one scalar input; probe budget {self.budget}; graded on the full input domain.")

    # ---- (de)serialization: the realized machine rides to the probe server in a server-only env ----
    def to_dict(self) -> dict:
        return {"name": self.name, "budget": self.budget,
                "outputs": [{"domain": o.domain, "weight": o.weight, "chain": list(o.chain)}
                            for o in self.outputs]}

    @classmethod
    def from_dict(cls, d: dict) -> "Machine":
        outs = tuple(Output(domain=o["domain"], weight=o["weight"],
                            chain=tuple(o["chain"])) for o in d["outputs"])
        return cls(name=d.get("name", "machine"), outputs=outs, budget=d["budget"])


# ---------------------------------------------------------------------------
# The builder: a blueprint (public, fixed per lineage) + a seed -> a fresh realized machine. The
# blueprint fixes the SHAPE (how many outputs, each one's domain and weight=chain length, and the
# kind mix); the seed re-rolls the HIDDEN part (each slot's kind and parameters) so every draw is a
# different machine of the same public shape — held-out generality by construction. The PI hand-
# authors one blueprint (instance 0); a draw is one disposable instance.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Blueprint:
    """The public shape. `slots` = one (domain, length) per output (length = weight, public). The
    HIDDEN kind of each slot is re-rolled per draw: with probability `p_affine` an affine chain
    (extrapolable), `p_const` a constant (a trap for anyone who forces a trend onto a flat signal),
    else an arbitrary table (predictable only where you read it). Only the kind + parameters re-roll;
    the public shape is identical across every draw, so a playbook must carry a method, not a case."""
    name: str
    slots: Tuple[Tuple[int, int], ...]   # (domain, chain_length) per output
    budget: int
    p_affine: float = 0.35
    p_const: float = 0.25

    def public_slots(self) -> List[dict]:
        """domain + weight(=length) per output — the public face, identical across every draw."""
        return [{"output": i, "domain": d, "weight": L} for i, (d, L) in enumerate(self.slots)]

    def to_dict(self) -> dict:
        return {"name": self.name, "slots": [list(s) for s in self.slots],
                "budget": self.budget, "p_affine": self.p_affine, "p_const": self.p_const}

    @classmethod
    def from_dict(cls, d: dict) -> "Blueprint":
        return cls(name=d["name"], slots=tuple(tuple(s) for s in d["slots"]),
                   budget=d["budget"], p_affine=d.get("p_affine", 0.35),
                   p_const=d.get("p_const", 0.25))


def _draw_affine_comp(rng: random.Random) -> dict:
    return {"t": "affine", "a": rng.choice(AFFINE_A), "b": rng.choice(AFFINE_B)}


def _draw_chain(rng: random.Random, domain: int, length: int,
                p_affine: float, p_const: float) -> List[dict]:
    """A fresh chain of the given length, of one hidden kind:
      * affine — all-affine components (observable affine; extrapolable from a few probes);
      * const  — a constant head + affine post-processing (still constant; the over-commit trap);
      * table  — a lookup head (parent = the input, table over the input domain) + affine
                 post-processing (an arbitrary table from outside; learnable only by reading it).
    The head fixes the kind; the affine tail makes the weight genuine upstream machinery."""
    roll = rng.random()
    if roll < p_affine:
        return [_draw_affine_comp(rng) for _ in range(length)]
    if roll < p_affine + p_const:
        head: dict = {"t": "const", "c": rng.randrange(M_VALUES)}
    else:
        head = {"t": "lookup", "table": [rng.randrange(M_VALUES) for _ in range(domain)]}
    return [head] + [_draw_affine_comp(rng) for _ in range(length - 1)]


def draw_machine(blueprint: Blueprint, seed: int) -> Machine:
    """Realize one fresh machine from the blueprint. Deterministic in `seed`: same seed -> same
    machine, so a score can always be replayed and train/held-out splits are reproducible."""
    rng = random.Random(seed)
    outs = []
    for (domain, length) in blueprint.slots:
        chain = _draw_chain(rng, domain, length, blueprint.p_affine, blueprint.p_const)
        outs.append(Output(domain=domain, weight=length, chain=tuple(chain)))
    return Machine(name=f"{blueprint.name}#{seed}", outputs=tuple(outs), budget=blueprint.budget)


# ---------------------------------------------------------------------------
# The scorer (PLAN.md §2). Only the exam pays; exact-match; abstain = blind-guess credit; zero = the
# strongest lazy constant; perfect = 1. A dumb deterministic function of the answer key + the
# submitted model — never an LLM, never the player's word for its own success.
# ---------------------------------------------------------------------------
def _blind_per_output(o: Output) -> Tuple[int, float]:
    """The best lazy constant for one output: the single value that, answered for every question,
    earns the most. Returns (its weighted credit, its hit rate p_o). For an affine over distinct
    inputs p_o = 1/domain; a const output is fully won by the lazy constant (p_o = 1)."""
    ans = o.answers()
    if not ans:
        return 0, 0.0
    counts: Dict[int, int] = {}
    for v in ans:
        counts[v] = counts.get(v, 0) + 1
    best = max(counts.values())
    return o.weight * best, best / len(ans)


def blind_baseline(machine: Machine) -> float:
    """Total credit of the best blind guesser = answering every output with its modal value =
    exactly the score of all-abstain. The zero point of the band."""
    return float(sum(_blind_per_output(o)[0] for o in machine.outputs))


def perfect_score(machine: Machine) -> float:
    """All questions correct — the band ceiling (norm 1)."""
    return float(sum(o.weight * o.domain for o in machine.outputs))


def normalize(raw: float, blind: float, perfect: float) -> float:
    """Map raw credit into the blind->perfect band. 0 = lazy/all-abstain, 1 = perfect; below 0 means
    confident wrong guessing did worse than abstaining (priced, not policed)."""
    band = perfect - blind
    if band <= 1e-9:
        return 0.0
    return (raw - blind) / band


def _predict(law: dict, x: int) -> Optional[int]:
    """A submitted law's prediction for one input, or None to abstain (unknown / malformed)."""
    if not isinstance(law, dict):
        return None
    kind = law.get("law")
    try:
        if kind == "const":
            return int(law["c"])
        if kind == "affine":
            return int(law["a"]) * x + int(law["b"])
        if kind == "table":
            vals = law.get("values") or {}
            for key in (x, str(x)):
                if key in vals:
                    return int(vals[key])
            return None
        return None  # "abstain", missing, or unknown
    except (KeyError, TypeError, ValueError):
        return None


def score_models(machine: Machine, models: Optional[dict]) -> dict:
    """Grade a per-output submission. `models` maps output index -> a law dict (see public_map's
    submit_format); omitted/abstain outputs earn the blind-guess credit. Returns the raw credit, the
    band, the normalized score, and a per-output breakdown for the (sanitized) report."""
    models = models or {}
    raw = 0.0
    per_output = []
    for i, o in enumerate(machine.outputs):
        law = models.get(i)
        if law is None:
            law = models.get(str(i))
        blind_o, p_o = _blind_per_output(o)
        abstain_credit = o.weight * p_o            # per-question blind credit (sums to blind_o)
        earned = 0.0
        n_correct = n_wrong = n_abstain = 0
        for x in range(o.domain):
            pred = _predict(law, x)
            if pred is None:
                earned += abstain_credit
                n_abstain += 1
            elif pred == o.f(x):
                earned += o.weight
                n_correct += 1
            else:
                n_wrong += 1                        # earns zero
        raw += earned
        per_output.append({
            "output": i, "domain": o.domain, "weight": o.weight, "kind": o.kind(),
            "law": (law.get("law") if isinstance(law, dict) else None) or "abstain",
            "earned": round(earned, 3), "perfect": o.weight * o.domain, "blind": blind_o,
            "correct": n_correct, "wrong": n_wrong, "abstain": n_abstain,
        })
    blind = blind_baseline(machine)
    perfect = perfect_score(machine)
    return {"raw": round(raw, 3), "blind": round(blind, 3), "perfect": round(perfect, 3),
            "norm": round(normalize(raw, blind, perfect), 4), "per_output": per_output}
