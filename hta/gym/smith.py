"""The **world-smith** — LOOP 2 (grow the WORLD; the curriculum). DESIGN.md §5-7 / ROADMAP "the two
loops".

The first loop evolves the *player* (the playbook) to a world's edge. This loop evolves the
*world's structure* to demand a kind of taste the current champion does NOT have — the curriculum
half. It proposes a harder world as a validated parts-list in the world language, then gates it.

The integrity wall, lifted to this loop (DESIGN.md §2): the inventor proposes only the world's
**structure** (a validated `WorldSpec` as data — safe-eval lifted, never code, never the score). The
referee (coverage) and the perfect-play oracle are re-derived **mechanically** by the unchanged
`hta.world.grade` machinery. A world **ships** only if it is still:
  * **hard**     — the belief-MDP oracle ≫ the best generic planner (`grade.screen`'s basket, incl.
                   2-step lookahead), so the right policy is not a shallow rule; and
  * **solvable** — a reachable method attains the oracle band; and
  * **fail-now-but-learnable (the ZPD)** — the *champion's* method stalls near the floor while the
    new method reaches the ceiling. The only legal coupling to the agent is this objective gap on the
    non-movable scorer, never the agent's internals (designing *around* the agent's weakness would be
    Goodhart at the curriculum level).

The champion/fix policies below are the model-free instruments of that ZPD check — articulable blind
adaptive policies (the same footing as `grade`'s basket) run through `grade.simulate`, so the verdict
is deterministic, token-free, and reproducible. They are NOT the agent (the agent is Haiku + the
English playbook); they are the necessary model-free screen that a structurally-harder world re-opens
a gap the champion's articulated rule cannot close — confirmed live by the closed-loop demonstration.

The first slice operates on a world's first FORK region (the structured region under test);
standalone clearings are budget mop-up. The curriculum's two moves mirror the trail's worked example:
instance0's decoy fork (commit-deepest fails -> scout-then-commit) and the gate ladder
(scout-the-first-gate fails -> scout the ladder adaptively).
"""

import json
import os
import re
from typing import Callable, Optional, Tuple

from ..dgmh import loop
from ..world import contract, grade
from ..world.instances import draw_hstar, instance0, ladder_world
from ..world.language import Fork, WorldSpec, validate

# Ship-gate thresholds. MARGIN/CLIFF/HEUR mirror the build-screen (the world must still clear it).
# SOLVE_BAR mirrors loop.SOLVED_BAR (reach the oracle band). FAIL_BAR: the champion's method counts as
# "fails by strategy" when it stalls at/under this much of the band.
MARGIN = 0.15
CLIFF = 0.55
HEUR_LO, HEUR_HI = 0.15, 0.80
SOLVE_BAR = 0.85
FAIL_BAR = 0.30


# ---------------------------------------------------------------------------
# Articulable methods, as blind adaptive policies over a world's first fork. Each is a
# `pick(table, cov, probe, costs, H, probed, b) -> col|None` closure (the `grade.simulate` contract),
# closing over the spec so it can walk the public chain topology — what a hand spec ("the method") may
# know — while staying blind to the hidden values (it reads only its refined belief H + the budget).
# ---------------------------------------------------------------------------
def _fork(spec: WorldSpec) -> Fork:
    forks = spec.forks()
    if not forks:
        raise ValueError("world-smith methods require a fork region")
    return forks[0]


def _index(spec: WorldSpec):
    """Map each signpost variable -> its pos-0 sig column (probing it pins that variable's value,
    since value = (var_value + 0) mod K), and list the clearing columns (for budget mop-up)."""
    sig_col, clearing_cols = {}, []
    for col, c in enumerate(spec.cells()):
        if c[0] == "sig" and c[2] == 0:
            sig_col[c[1]] = col
        elif c[0] == "direct":
            clearing_cols.append(col)
    return sig_col, clearing_cols


def _pinned(table, H, col) -> Optional[int]:
    """The value all surviving hypotheses agree on at `col`, or None if they still disagree."""
    if col is None:
        return None
    rep = next(iter(H))
    v = table[rep][col]
    return v if all(table[h][col] == v for h in H) else None


def _walk_pick(spec: WorldSpec, fork: Fork, sig_col, clearing_cols, chain_of):
    """Build a pick that walks the chain `chain_of(table, H)` selects, probing the first un-pinned
    chain variable, then mops up clearings with leftover budget. Shared spine of both methods."""
    K = spec.K

    def pick(table, cov, probe, costs, H, probed, b):
        chain = chain_of(table, H)
        if chain is not None:
            r, path = chain.head, [chain.head]
            for hop in chain.hops:
                v = _pinned(table, H, sig_col.get(r))
                if v is None:
                    break
                r = hop[v % K]
                path.append(r)
            for reg in path:
                col = sig_col.get(reg)
                if col is not None and col not in probed and costs[col] <= b:
                    return col
        for col in clearing_cols:           # chain walked (or none yet) -> spend the rest on clearings
            if col not in probed and costs[col] <= b:
                return col
        return None
    return pick


def commit_deepest(spec: WorldSpec) -> Callable:
    """The depth-committing method: commit to the deepest-looking chain and reconstruct its valley,
    never scouting the gate. Wins a single trail — but on a fork it walks a chain whose valley never
    resolves without the gate, so it stalls at the floor. (Ties in depth -> the first chain.)"""
    fork = _fork(spec)
    sig_col, clearing_cols = _index(spec)
    deepest = max(fork.chains, key=lambda ch: ch.depth)
    return _walk_pick(spec, fork, sig_col, clearing_cols, lambda table, H: deepest)


def scout_then_commit(spec: WorldSpec) -> Callable:
    """Read THE gate FIRST (the cheap feasibility scout), then commit to the LIVE chain it names, then
    mop up. Reaches the oracle band on a single-gate fork. On a gate LADDER it reads only the FIRST
    gate, so it commits without scouting the rest of the ladder — and fails the ladder the same way
    commit-deepest failed the decoy."""
    fork = _fork(spec)
    sig_col, clearing_cols = _index(spec)
    gate_col = sig_col.get(fork.gate)
    K, n = spec.K, fork.n_chains

    def chain_of(table, H):
        gv = _pinned(table, H, gate_col)
        if n > 1 and gv is None:
            return None                     # gate not yet pinned -> scout it before committing
        return fork.chains[(gv or 0) % n]

    base = _walk_pick(spec, fork, sig_col, clearing_cols, chain_of)

    def pick(table, cov, probe, costs, H, probed, b):
        if n > 1 and _pinned(table, H, gate_col) is None:   # explicit scout step (real fork)
            if gate_col is not None and gate_col not in probed and costs[gate_col] <= b:
                return gate_col
        return base(table, cov, probe, costs, H, probed, b)
    return pick


def _ladder_walk(spec: WorldSpec, fork: Fork, sig_col, table, H):
    """Walk the gate ladder by the values pinned SO FAR. Returns (var, done): if a gate's value is not
    yet pinned, (that gate var, False) — the next to scout; else (final gate var, True) once the whole
    ladder resolves. With no gate_hops this is just (gate, gate-pinned?)."""
    r = fork.gate
    for hop in fork.gate_hops:
        v = _pinned(table, H, sig_col.get(r))
        if v is None:
            return r, False
        r = hop[v % spec.K]
    return r, _pinned(table, H, sig_col.get(r)) is not None


def scout_ladder_then_commit(spec: WorldSpec) -> Callable:
    """Scout the gate ladder ADAPTIVELY — read the gate, let its value name the next gate, ... to the
    final gate — THEN commit to the live chain it names and walk it. Reaches the oracle band on the
    ladder; generalizes scout_then_commit (which is this with a zero-rung ladder)."""
    fork = _fork(spec)
    sig_col, clearing_cols = _index(spec)
    K, n = spec.K, fork.n_chains

    def chain_of(table, H):
        r, done = _ladder_walk(spec, fork, sig_col, table, H)
        if n > 1 and not done:
            return None                     # ladder not fully scouted -> keep scouting
        gv = _pinned(table, H, sig_col.get(r))
        return fork.chains[(gv or 0) % n]

    base = _walk_pick(spec, fork, sig_col, clearing_cols, chain_of)

    def pick(table, cov, probe, costs, H, probed, b):
        if n > 1:                           # adaptive scout: probe the next un-pinned gate
            r, done = _ladder_walk(spec, fork, sig_col, table, H)
            if not done:
                col = sig_col.get(r)
                if col is not None and col not in probed and costs[col] <= b:
                    return col
        return base(table, cov, probe, costs, H, probed, b)
    return pick


def policy_band(spec: WorldSpec, make_pick: Callable) -> Tuple[float, float]:
    """Run an articulable method against every true world and normalize its mean determined-cells into
    the model-free floor->oracle band. Returns (norm, raw)."""
    raw = grade.simulate(spec, make_pick(spec))
    norm = grade.normalize(raw, grade.floor_value(spec), grade.oracle_value(spec))
    return norm, raw


# ---------------------------------------------------------------------------
# The ship-gate: the model-free verdict on whether a proposed world may ship (hard + solvable + the
# ZPD: the champion fails, the fix succeeds). Free, deterministic, token-free.
# ---------------------------------------------------------------------------
def ship_gate(spec: WorldSpec, champion_method: Callable = commit_deepest,
              fix_method: Callable = scout_then_commit) -> dict:
    """The model-free verdict on one structural move. `champion_method` is the CURRENT champion's
    articulated rule (the one the move must break); `fix_method` is the reachable disposition that
    closes it (the ZPD's upper edge)."""
    issues = validate(spec)
    s = grade.screen(spec, clair=False)
    champ_norm, champ_raw = policy_band(spec, champion_method)
    fix_norm, fix_raw = policy_band(spec, fix_method)

    hard = s["gap_norm"] >= MARGIN
    solvable = fix_norm >= SOLVE_BAR and s["oracle"] > s["floor"] + 1e-9
    ramp_ok = s["ramp_monotone"] and s["ramp_maxstep"] <= CLIFF
    room = HEUR_LO <= s["heur_norm"] <= HEUR_HI
    champion_fails = champ_norm <= FAIL_BAR
    ship = bool(not issues and hard and solvable and ramp_ok and champion_fails)
    return {
        "name": spec.name, "valid": not issues, "issues": issues,
        "floor": s["floor"], "best_heur": s["best_heur"], "oracle": s["oracle"],
        "gap_norm": s["gap_norm"], "heur_norm": s["heur_norm"],
        "ramp_maxstep": s["ramp_maxstep"], "ramp_monotone": s["ramp_monotone"],
        "champion_norm": champ_norm, "champion_raw": champ_raw,
        "fix_norm": fix_norm, "fix_raw": fix_raw,
        "hard": hard, "solvable": solvable, "ramp_ok": ramp_ok, "room": room,
        "champion_fails": champion_fails, "ship": ship,
    }


# ---------------------------------------------------------------------------
# The inventor plane (Opus). It proposes the world's STRUCTURE as data; the harness validates,
# realizes, and gates it. For the first deliverable the moves are hand-authored (as instance 0 was)
# and `propose_move` returns one; the live-inventor hook is `realize_proposal`.
# ---------------------------------------------------------------------------
INVENTOR_INSTRUCTION = """You design the next world in a curriculum that grows a research agent's taste.

The agent investigates a hidden world under a scarce probe budget, scored only by objective COVERAGE
(how many cells its probes logically pin). You are shown the current champion's playbook and a
sanitized record of how it just investigated. Your job: propose the STRUCTURE of a harder world that
demands a kind of investigation the champion's playbook does NOT yet do — a deeper, branching, or
gated trail — never merely a bigger number or a tighter budget.

You propose only STRUCTURE, as a JSON object (a world parts-list): variables R, colors K, a `budget`,
and a list of `regions`. Each region is either {"kind":"clearing","var":i,"Ld":n} (a variable paying
n cells immediately) or {"kind":"fork","gate":g,"Lv":n,"gate_hops":[[..K..],...],"chains":[{"head":h,
"hops":[[..K..],...]},...]} (a gate ladder selecting which chain is live; its live chain drives a deep
n-cell valley). You do NOT propose the score or the oracle — the harness re-derives those mechanically
from your structure and will only ship your world if it is still HARD (a belief-MDP oracle beats every
generic planner) and SOLVABLE within budget, and if the champion measurably fails it while the right
method succeeds. Reason about WHICH behavior the champion lacks; emit one JSON object, nothing else."""


def realize_proposal(text: str) -> Tuple[Optional[WorldSpec], list]:
    """Realize an inventor proposal: extract the JSON parts-list, build the spec (data, never executed
    — safe-eval lifted), and validate it. Returns (spec or None, issues)."""
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        return None, ["no JSON object found in the proposal"]
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return None, [f"malformed JSON: {e}"]
    d.setdefault("name", "proposed")
    return contract.realize(d)


def propose_move(champion_dir: str = None, cfg=None, log=print) -> WorldSpec:
    """The world-smith's structural move past instance 0's champion. Hand-authored for the first
    deliverable (the gate ladder), the way instance 0 was; the live inventor would emit it via
    `INVENTOR_INSTRUCTION` -> `realize_proposal`. Accounting for the instance-0 graduate's rule (scout
    THE gate, then commit), the move makes the gate an adaptive ladder that one scout cannot disarm."""
    return ladder_world()


# ---------------------------------------------------------------------------
# The closed-loop demonstration (LIVE when cfg.backend == 'real'): eval the champion on fresh draws of
# the harder world (it should fail by strategy), run ONE coaching round (Opus rewrites the playbook
# from the champion's conduct on THIS world), eval the new player on fresh held-out draws (it should
# pass). Reuses the first loop's machinery wholesale (`loop.evaluate`, `loop.meta_edit`).
# ---------------------------------------------------------------------------
def demonstrate(champion_dir: str, spec: WorldSpec, cfg, n_eval: int = 4,
                seed: int = 990_000, child_name: str = "coached", log=print) -> dict:
    worlds_before = [(spec, draw_hstar(spec, seed + i)) for i in range(n_eval)]
    log(f"\n[eval CHAMPION on '{spec.name}' — {n_eval} fresh draws; expect failure by strategy]")
    champ = loop.evaluate(champion_dir, worlds_before, cfg, log=log)
    log(f"  => champion mean_norm={champ['mean_norm']:.2f} solved={champ['solved']}/{champ['n_worlds']}")

    child_dir = os.path.join(cfg.out_dir, "gym", child_name)
    log("\n[one coaching round: Opus rewrites the playbook from the champion's conduct on this world]")
    loop.meta_edit(champion_dir, child_dir, champ["report_md"], cfg, log=log)

    worlds_after = [(spec, draw_hstar(spec, seed + 5_000 + i)) for i in range(n_eval)]
    log(f"\n[eval COACHED player on '{spec.name}' — {n_eval} fresh HELD-OUT draws; expect it passes]")
    coached = loop.evaluate(child_dir, worlds_after, cfg, log=log)
    log(f"  => coached mean_norm={coached['mean_norm']:.2f} solved={coached['solved']}/{coached['n_worlds']}")

    return {"champion": champ, "coached": coached, "child_dir": child_dir,
            "closed": coached["mean_norm"] - champ["mean_norm"]}


# ---------------------------------------------------------------------------
# The curriculum — the two-loop run as a sequence of structural MOVES. Each move is a ZPD step: a
# harder world, the CURRENT champion's articulated rule (the move must break it), and the reachable
# fix (the move must be solvable by it). The coached player carries forward as the next champion, so
# move 2's champion is move 1's graduate — the outer loop closing on itself.
# ---------------------------------------------------------------------------
CURRICULUM = [
    {"label": "move 1 — the DECOY fork (scout THE gate, then commit)",
     "spec": instance0, "champion": commit_deepest, "fix": scout_then_commit, "child_name": "coached_1"},
    {"label": "move 2 — the gate LADDER (scout ADAPTIVELY, then commit)",
     "spec": ladder_world, "champion": scout_then_commit, "fix": scout_ladder_then_commit,
     "child_name": "coached_2"},
]


def run_curriculum(champion_dir: str, cfg, n_eval: int = 4, log=print) -> list:
    """Run the structural moves in order, the coached player from each carrying forward as the next
    move's champion. Each move is ship-gated model-free first (it must SHIP — hard + solvable + this
    champion fails) and then demonstrated live. Returns a per-move record; `child_dir` of the LAST
    move is the final champion."""
    champ_dir = champion_dir
    out = []
    for i, mv in enumerate(CURRICULUM):
        spec = mv["spec"]()
        log("\n" + "#" * 100)
        log(f"# {mv['label']}")
        log("#" * 100)
        gate = ship_gate(spec, champion_method=mv["champion"], fix_method=mv["fix"])
        log(f"  ship-gate '{spec.name}': gap {gate['gap_norm']:.2f}n  champion {gate['champion_norm']:.2f}n"
            f"  fix {gate['fix_norm']:.2f}n  ==> {'SHIP' if gate['ship'] else 'HOLD'}")
        if not gate["ship"]:
            log("  this move does not ship model-free; stopping the curriculum.")
            out.append({"label": mv["label"], "spec": spec.name, "gate": gate, "rep": None})
            break
        rep = demonstrate(champ_dir, spec, cfg, n_eval=n_eval, seed=990_000 + 100_000 * i,
                          child_name=mv["child_name"], log=log)
        out.append({"label": mv["label"], "spec": spec.name, "gate": gate, "rep": rep})
        champ_dir = rep["child_dir"]            # the graduate becomes the next champion
    return out
