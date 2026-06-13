"""Model-free QA for the machine world (PLAN.md §3, gate 1 — "Too easy?"). These are **unit tests of
the world, not baselines for the agent**: scripted probers that drive the machine through the same
budget the player gets and submit a model the same scorer grades. If a dumb scripted prober already
scores well, the world does not measure taste and must be reshaped. All free, deterministic, no LLM.

Three scripted probers (each must land ≈ 0 of the band) plus one **reference tasteful** allocator
(must land well above) — the headroom check that there is a real gap for the inner loop to grow into:

  * `random_poke`     — probe random (output,input) cells, submit only what was seen, abstain else.
                        Covers a sliver of the exam -> ≈ blind.
  * `sweep_fit`       — even probes per output, fit an affine and COMMIT it everywhere, never checking,
                        never abstaining. Wins true-affine outputs, but commits a wrong line on tables
                        -> ≈ 0 (or below) when tables carry the mass.
  * `enumerate_even`  — even probes per output, submit a partial table, abstain elsewhere. Honest but
                        unfocused: a thin smear resolves nothing fully -> low.
  * `reference_tasteful` — read weight + scout each output's kind, EXTRAPOLATE the affines cheaply,
                        ENUMERATE the affordable tables, ABSTAIN on the rest. Concentration + check +
                        calibration. The model-free proof the gap exists; NOT a runtime baseline (the
                        live student is the only ZPD oracle, PLAN.md §3 gate 3).
"""

import random
from typing import Dict, List

from .machine import Machine, Output, score_models


# ---------------------------------------------------------------------------
# A tiny probe budget harness: a scripted prober reads f_o(x) (the answer key — it is lab-side,
# model-free) and pays one unit of budget per read, exactly like the live player's `probe`.
# ---------------------------------------------------------------------------
class _Probe:
    def __init__(self, machine: Machine):
        self.machine = machine
        self.remaining = machine.budget
        self.seen: Dict[int, Dict[int, int]] = {i: {} for i in range(len(machine.outputs))}

    def read(self, o: int, x: int) -> bool:
        if self.remaining <= 0 or x in self.seen[o]:
            return x in self.seen[o]
        self.seen[o][x] = self.machine.outputs[o].f(x)
        self.remaining -= 1
        return True


def _affine_from(samples: List[tuple]):
    """Fit a*x+b from sorted (x, y) samples iff they lie on one integer-step line; else None."""
    if len(samples) < 2:
        return None
    (x0, y0), (x1, y1) = samples[0], samples[1]
    dx = x1 - x0
    if dx == 0 or (y1 - y0) % dx != 0:
        return None
    a = (y1 - y0) // dx
    b = y0 - a * x0
    if all(y == a * x + b for x, y in samples):
        return {"law": "affine", "a": a, "b": b}
    return None


def _table_law(seen: Dict[int, int]) -> dict:
    return {"law": "table", "values": {str(x): v for x, v in seen.items()}}


# ---------------------------------------------------------------------------
# The scripted probers. Each returns the score dict from the shared scorer.
# ---------------------------------------------------------------------------
def random_poke(machine: Machine, seed: int = 0) -> dict:
    rng = random.Random(seed)
    p = _Probe(machine)
    cells = [(o, x) for o in range(len(machine.outputs)) for x in range(machine.outputs[o].domain)]
    rng.shuffle(cells)
    for o, x in cells:
        if p.remaining <= 0:
            break
        p.read(o, x)
    models = {o: _table_law(p.seen[o]) for o in range(len(machine.outputs)) if p.seen[o]}
    return score_models(machine, models)


def _even_probe(machine: Machine) -> _Probe:
    """Spread the budget evenly: one round-robin pass over inputs across all outputs until spent."""
    p = _Probe(machine)
    n = len(machine.outputs)
    x = 0
    while p.remaining > 0 and x < max((o.domain for o in machine.outputs), default=0):
        for o in range(n):
            if p.remaining <= 0:
                break
            if x < machine.outputs[o].domain:
                p.read(o, x)
        x += 1
    return p


def sweep_fit(machine: Machine, seed: int = 0) -> dict:
    """Fit an affine to each output's probes and COMMIT it over the whole domain — no check, no
    abstain. The over-committer: right on real lines, wrong on tables."""
    p = _even_probe(machine)
    models = {}
    for o in range(len(machine.outputs)):
        seen = sorted(p.seen[o].items())
        if not seen:
            continue
        if len(seen) == 1:
            models[o] = {"law": "const", "c": seen[0][1]}
            continue
        (x0, y0), (x1, y1) = seen[0], seen[1]
        dx = x1 - x0 or 1
        a = (y1 - y0) // dx
        models[o] = {"law": "affine", "a": a, "b": y0 - a * x0}   # commit, even if the fit is bad
    return score_models(machine, models)


def enumerate_even(machine: Machine, seed: int = 0) -> dict:
    """Even probes, honest partial tables, abstain elsewhere. Unfocused but not reckless."""
    p = _even_probe(machine)
    models = {o: _table_law(p.seen[o]) for o in range(len(machine.outputs)) if p.seen[o]}
    return score_models(machine, models)


def reference_tasteful(machine: Machine, seed: int = 0) -> dict:
    """The headroom policy: by descending weight, scout each output's kind; extrapolate affines for
    a few probes, enumerate the affordable tables, abstain on what the budget can't reach. Greedy,
    not optimal — it only has to prove the gap above the scripted floor is real."""
    p = _Probe(machine)
    outs = machine.outputs
    order = sorted(range(len(outs)), key=lambda i: (-outs[i].weight, outs[i].domain))
    models: Dict[int, dict] = {}
    for i in order:
        o: Output = outs[i]
        scout = min(3, o.domain)
        for x in range(scout):
            if p.remaining <= 0:
                break
            p.read(i, x)
        seen = sorted(p.seen[i].items())
        if not seen:
            models[i] = {"law": "abstain"}
            continue
        vals = [v for _, v in seen]
        if len(set(vals)) == 1 and len(seen) >= 2:
            models[i] = {"law": "const", "c": vals[0]}   # flat signal -> don't force a trend
            continue
        affine = _affine_from(seen)
        if affine is not None:
            models[i] = affine                      # cheap full credit
            continue
        # a table: enumerate the rest iff the budget can finish it, else keep the partial + abstain
        need = [x for x in range(o.domain) if x not in p.seen[i]]
        if len(need) <= p.remaining:
            for x in need:
                p.read(i, x)
        models[i] = _table_law(p.seen[i])
    return score_models(machine, models)


SCRIPTED = {"random_poke": random_poke, "sweep_fit": sweep_fit, "enumerate_even": enumerate_even}


def screen_blueprint(blueprint, seeds=range(40)) -> dict:
    """Average the scripted floor and the tasteful ceiling over many fresh draws (luck washes out).
    Returns the per-prober mean norm + the gap, so the build-screen can verdict the world."""
    from .machine import draw_machine
    sums = {k: 0.0 for k in SCRIPTED}
    sums["reference_tasteful"] = 0.0
    seeds = list(seeds)
    for s in seeds:
        m = draw_machine(blueprint, 7919 * (s + 1))
        for k, fn in SCRIPTED.items():
            sums[k] += fn(m, seed=s)["norm"]
        sums["reference_tasteful"] += reference_tasteful(m, seed=s)["norm"]
    means = {k: round(v / len(seeds), 4) for k, v in sums.items()}
    floor = max(means[k] for k in SCRIPTED)
    means["scripted_floor"] = floor
    means["gap"] = round(means["reference_tasteful"] - floor, 4)
    return means
