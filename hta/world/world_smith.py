"""World-smith: the Opus curriculum generator.

It builds *training* worlds (whose difficulty it grows toward the agent's zone of
proximal development, and which it biases toward situations where research taste --
falsification, edge-case probing -- is what makes the difference) and exposes a
FROZEN *transfer* suite that it does not adapt, so generalization can be measured
fairly.

Generated rules are validated through the same strict AST whitelist as everything
else (hta.world.grammar) before they are ever compiled, so model output cannot
execute arbitrary code. Two further gates (WORLD_DESIGN.md) keep the curriculum
honest as worlds get richer:
  * a *solvability gate* -- a generated world is rejected unless it is non-degenerate
    (produces both labels, not a near-constant) and solvable-in-principle (a
    reference Occam inductor with a generous probe budget recovers its equivalence
    class). This is the ZPD floor: the smith can't hand the agent unsolvable or
    trivial worlds.
  * a *behavior-vector novelty* gate -- two worlds whose label vectors over the
    battery are within a small Hamming distance are de-duplicated, an objective,
    model-free "is this actually a new world" check.
"""

import json
import random
from typing import List, Optional

from .. import llm
from ..config import Config
from .grammar import (RuleSpec, candidate_library, sample_hypotheses,
                      validate_lambda)
from .engine import WiltWorld, battery, behavior_vector

_SMITH_PROMPT = """You are the WORLD-SMITH for an inductive-reasoning curriculum.
Invent hidden boolean rules over three numbers (x, y, z) for a Wason 2-4-6 style
task. Each rule is a Python lambda returning a bool, using only x, y, z, numeric
literals, comparisons, and/or/not, + - * / % ** //, and abs/min/max.

Design rules so that *research taste* is what separates good from bad solvers:
prefer rules where naive "confirm my guess" probing fails but falsifying, edge-case
probing (boundaries like <= vs <, rare exceptions, sign/zero cases) succeeds.

COMPOSE rules -- don't just emit one atomic comparison. Climb this structure axis:
  - atomic     : one comparison/relation, e.g. `x < y < z`
  - conjunction: compose two partial hypotheses, e.g. `(x < y < z) and (x+y+z > 0)`
  - regime     : different rule in different regions, e.g.
                 `(x < y < z) if x < 0 else (x > y > z)` -- rewards noticing the
                 world behaves differently in two regions.
  - exception  : a rule with a carved-out hole, e.g. `x < y < z and not (z-x == 4)`
                 -- looks like plain "increasing" until you probe the exception;
                 confirm-only probing never finds it.
Report each rule's `structure` (one of atomic/conjunction/regime/exception).

Target difficulty around {target_difficulty}/5 (1=easy, 5=hard). Escalate from what
the agent already handles. Each rule must be non-degenerate (true on SOME inputs and
false on others, not nearly always one) and solvable by a careful prober.

Target the agent's WEAK areas (tags it currently fails): {weak_tags}. Bias the rules
toward exercising those weaknesses, so the agent must improve its taste to win.

Frontier (what the current best agent is weak at): {frontier}

Return ONLY JSON:
{{"rules": [{{"name": "...", "source": "lambda x, y, z: ...", "difficulty": N,
             "structure": "regime", "tags": ["falsification", "edge_cases", ...]}}, ...]}}
Return exactly {n} rules.

<<CTX>>{ctx}<<CTX>>"""

# An independently-seeded held-out transfer distribution (WORLD_DESIGN.md): drawn
# with a FIXED seed that is never conditioned on the agent's weak_tags, so transfer
# is a genuine held-out distribution rather than a short, memorizable hand-list.
_TRANSFER_SEED = 0x7A5E

# Solvability / novelty gate parameters.
_MIN_LABEL_COUNT = 5      # both True and False must occur >= this on the battery.
                          # (An absolute floor, not the ~5% fraction in the design
                          # note: the battery's structured composition puts classic
                          # rules like all_equal/sum_eq at ~1-2%, so a 5% fraction
                          # floor would wrongly reject them -- this kills constants
                          # and near-constants while keeping legitimate sparse rules.)
_NOVELTY_HAMMING = 4      # behavior vectors closer than this are near-duplicates.
_RECOVER_BUDGET = 40      # generous probe budget for the reference inductor.

# Caches: the gate is rerun every iteration over the same library, so memoize the
# fixed decoy label matrices (computed once) and per-rule admissibility/behavior.
_DECOY_PROBE_MAT = None   # decoy labels over the probe-candidate points
_DECOY_FULL_MAT = None    # decoy labels over the full battery (for equivalence)
_ADMISSIBLE_CACHE = {}
_BEHAVIOR_CACHE = {}


def _decoy_matrices():
    """Precompute, once, the label vectors of a fixed decoy pool (library + sampled
    grammar) over (a) the probe candidates and (b) the full battery. Vectorizing here
    keeps the reference inductor a pure integer computation per candidate rule."""
    global _DECOY_PROBE_MAT, _DECOY_FULL_MAT
    if _DECOY_PROBE_MAT is None:
        specs = (candidate_library()
                 + sample_hypotheses(0xC0FFEE, 48, "exception", include_library=False))
        bat = battery()
        _DECOY_FULL_MAT = [tuple(bool(s.fn(*t)) for t in bat) for s in specs]
        _DECOY_PROBE_MAT = _DECOY_FULL_MAT  # probe candidates = the full battery
    return _DECOY_PROBE_MAT, _DECOY_FULL_MAT


# ---------------------------------------------------------------------------
# Solvability gate
# ---------------------------------------------------------------------------
def _non_degenerate(fn) -> bool:
    """True iff the rule labels both True and False at least _MIN_LABEL_COUNT times
    over the battery (kills constant / near-constant rules)."""
    trues = sum(1 for t in battery() if fn(*t))
    falses = len(battery()) - trues
    return trues >= _MIN_LABEL_COUNT and falses >= _MIN_LABEL_COUNT


def _reference_recovers(rule: RuleSpec, budget: int = _RECOVER_BUDGET) -> bool:
    """Reference Occam inductor (solvable-in-principle check). The pool is the fixed
    decoy set plus the true rule; the prober greedily picks the probe that ELIMINATES
    the most decoys inconsistent with the true label, up to a generous budget. The
    world is solvable iff the survivors are all empirically equivalent to the true
    rule -- i.e. an optimal, falsification-driven prober pins its equivalence class
    within the budget. (Vectorized over precomputed label matrices.)"""
    probe_mat, full_mat = _decoy_matrices()
    truth_full = _behavior(rule)             # labels over the full battery
    truth_probe = truth_full                 # probe candidates == full battery
    live = list(range(len(probe_mat)))       # indices of decoys still consistent
    asked = set()
    for _ in range(budget):
        if not live:
            break
        best_p, best_surv = None, None
        for p in range(len(truth_probe)):
            if p in asked:
                continue
            lbl = truth_probe[p]
            surv = sum(1 for i in live if probe_mat[i][p] == lbl)
            if surv < len(live) and (best_surv is None or surv < best_surv):
                best_surv, best_p = surv, p
        if best_p is None:
            break  # no remaining probe eliminates any surviving decoy
        asked.add(best_p)
        lbl = truth_probe[best_p]
        live = [i for i in live if probe_mat[i][best_p] == lbl]
    return all(full_mat[i] == truth_full for i in live)


def is_admissible(rule: RuleSpec) -> bool:
    """A world is admissible iff its rule is safe, non-degenerate, and solvable.
    Memoized by source (the same library is gated every iteration)."""
    if rule.source in _ADMISSIBLE_CACHE:
        return _ADMISSIBLE_CACHE[rule.source]
    ok = False
    if validate_lambda(rule.source):
        try:
            ok = _non_degenerate(rule.fn) and _reference_recovers(rule)
        except Exception:
            ok = False
    _ADMISSIBLE_CACHE[rule.source] = ok
    return ok


def _behavior(rule: RuleSpec):
    if rule.source not in _BEHAVIOR_CACHE:
        _BEHAVIOR_CACHE[rule.source] = behavior_vector(rule.fn)
    return _BEHAVIOR_CACHE[rule.source]


# ---------------------------------------------------------------------------
# Behavior-vector novelty
# ---------------------------------------------------------------------------
def _hamming(a, b) -> int:
    return sum(1 for u, v in zip(a, b) if u != v)


def _is_novel(vec, seen_vecs, min_dist: int = _NOVELTY_HAMMING) -> bool:
    return all(_hamming(vec, s) >= min_dist for s in seen_vecs)


def select_worlds(candidates: List[RuleSpec], n: int, seen_vecs=None) -> List[RuleSpec]:
    """Pick up to `n` rules that are admissible (solvable + non-degenerate) and
    behaviorally novel (battery label-vector far from already-chosen / `seen_vecs`).
    Falls back to relaxing novelty, then admissibility, so it never returns fewer than
    min(n, len(candidates)) worlds -- a short curriculum would stall the loop."""
    chosen, vecs = [], list(seen_vecs or [])
    deferred_dup, deferred_inadmissible = [], []
    for r in candidates:
        if len(chosen) >= n:
            break
        try:
            vec = _behavior(r)
        except Exception:
            continue
        if not is_admissible(r):
            deferred_inadmissible.append((r, vec))
            continue
        if not _is_novel(vec, vecs):
            deferred_dup.append((r, vec))
            continue
        chosen.append(r)
        vecs.append(vec)
    # backfill: prefer admissible-but-duplicate, then anything, to reach n.
    for bucket in (deferred_dup, deferred_inadmissible):
        for r, vec in bucket:
            if len(chosen) >= n:
                break
            chosen.append(r)
            vecs.append(vec)
    return chosen[:n]


def _rulespecs_from_json(text: str) -> List[RuleSpec]:
    obj = llm.extract_json(text) or {}
    out = []
    for r in obj.get("rules", []):
        src = r.get("source", "")
        if validate_lambda(src):
            out.append(RuleSpec(r.get("name", "rule"), src, r.get("difficulty", 3),
                                tuple(r.get("tags", ())), r.get("structure", "atomic")))
    return out


def build_worlds(cfg: Config, target_difficulty: int = 2, weak_tags=None,
                 frontier: Optional[str] = None, log=print) -> List[WiltWorld]:
    n = cfg.n_train_worlds
    weak_tags = list(weak_tags or [])
    ctx = json.dumps({"role": "world_smith", "n": n,
                      "target_difficulty": target_difficulty, "weak_tags": weak_tags})
    prompt = _SMITH_PROMPT.format(target_difficulty=target_difficulty,
                                  frontier=frontier or "(none yet)", n=n, ctx=ctx,
                                  weak_tags=", ".join(weak_tags) or "(none yet)")
    try:
        text = llm.complete(prompt, model=cfg.world_model, role="world_smith", cfg=cfg)
        rules = _rulespecs_from_json(text)
    except Exception as e:
        log(f"  world-smith fell back to library: {e}")
        rules = []
    # backfill candidates from the library, preferring rules whose tags hit the weak
    # areas and whose difficulty is near the target. These sit AFTER the smith's own
    # rules so generated worlds are tried first, then the gate/novelty selection runs.
    weak = set(weak_tags)
    lib = candidate_library()
    lib.sort(key=lambda r: (-len(set(r.tags) & weak), abs(r.difficulty - target_difficulty)))
    have = {r.source for r in rules}
    candidates = list(rules) + [r for r in lib if r.source not in have]

    # de-dup training worlds against each other AND against the frozen transfer set,
    # so the curriculum can't accidentally hand the agent a relabeled transfer world.
    transfer_vecs = []
    for w in transfer_suite(cfg):
        try:
            transfer_vecs.append(_behavior(w.rule))
        except Exception:
            pass
    chosen = select_worlds(candidates, n, seen_vecs=transfer_vecs)
    structs = {}
    for r in chosen:
        structs[r.structure] = structs.get(r.structure, 0) + 1
    log(f"  world-smith built {len(chosen)} training worlds "
        f"(target_difficulty={target_difficulty}, weak_tags={weak_tags or 'none'}, "
        f"structures={structs})")
    return [WiltWorld(r, max_probes=cfg.max_probes) for r in chosen]


def transfer_suite(cfg: Config) -> List[WiltWorld]:
    """Frozen, independently-seeded held-out worlds. Drawn from the grammar's library
    prior with a FIXED seed that never sees the agent's weak_tags, so transfer is a
    genuine held-out distribution rather than a fixed, memorizable hand-list. Only
    admissible (solvable + non-degenerate) worlds are kept."""
    pool = [r for r in candidate_library() if is_admissible(r)]
    random.Random(_TRANSFER_SEED).shuffle(pool)
    chosen = select_worlds(pool, cfg.n_transfer_worlds)
    return [WiltWorld(r, max_probes=cfg.max_probes) for r in chosen]
