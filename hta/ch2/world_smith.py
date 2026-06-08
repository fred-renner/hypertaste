"""The **world-smith** — the second loop (ROADMAP.md -> "The two loops" / "Closing the outer loop").

The first loop evolves the *player* (the playbook) to the world's edge. This loop evolves the
*world's structure* to demand a kind of taste the current champion does **not** have — the
curriculum half. Its first deliverable is the **closed-loop demonstration**: author a structurally
harder world, show the champion fails *by strategy* (not luck), run one coaching round, show the new
player passes.

What the harder world is (`worlds.decoy_spec`): a **forked** trail. The champion's grown note on the
anchor was "list every chain, count payoff-per-dig, commit to the deepest." That wins a single trail
and survives every *scalar* crank (`run_probe.py`). The fork breaks it: the valley mirrors the LIVE
chain's landmark, and which chain is live is a GATE register's hidden value, so committing to a chain
without the cheap gate scout pins zero valley — whichever chain it is. The new taste the world
demands is **scout feasibility, then commit**.

The integrity wall, lifted to this loop (ROADMAP.md -> "The integrity floor"; "Closing the outer
loop"): the inventor proposes only the world's **structure** (a validated `ForkedTrailSpec` as data —
safe-eval lifted, never code, never the score). The referee (coverage) and the perfect-play oracle
are re-derived **mechanically** by the unchanged `anchor.py` machinery. A world **ships** only if it
is still:
  * **hard**     — the belief-MDP oracle ≫ the best *generic* planner (`anchor.screen`'s basket,
                   incl. 2-step lookahead), so the right policy is not a shallow rule; and
  * **solvable** — a reachable *method* (scout-then-commit) attains the oracle band; and
  * **fail-now-but-learnable (the ZPD)** — the *champion's* method (commit-to-the-deepest) stalls
    near the floor, while the new method reaches the ceiling. The only legal coupling to the agent is
    this **objective gap on the non-movable scorer**, never the agent's internals (designing *around*
    the agent's weakness would be Goodhart at the curriculum level).

The two policies below are the model-free instruments of that ZPD check — articulable blind adaptive
policies (the same footing as `anchor`'s basket) that model the champion's method and its fix, run
through the exact `anchor._simulate` so the verdict is deterministic, token-free, and reproducible.
They are NOT the agent (the agent is Haiku + the English playbook); they are the *necessary*
model-free screen that a structurally-harder world re-opens a gap the champion's articulated rule
cannot close — the world-smith's analogue of `run_anchor.py`'s build-screen, confirmed live by the
closed-loop demonstration.
"""

import json
import os
import re
from typing import Callable, Optional, Tuple

from . import anchor, loop, worlds
from .episode_state import draw_hstar, normalize
from .worlds import ForkedTrailSpec

# Ship-gate thresholds. MARGIN/CLIFF/HEUR mirror run_anchor.py (the world must still clear the
# build-screen). SOLVE_BAR mirrors loop.SOLVED_BAR (reach the oracle band). FAIL_BAR: the champion's
# method counts as "fails by strategy" when it stalls at/under this much of the band.
MARGIN = 0.15
CLIFF = 0.55
HEUR_LO, HEUR_HI = 0.15, 0.80
SOLVE_BAR = 0.85
FAIL_BAR = 0.30


# ---------------------------------------------------------------------------
# Articulable methods, as blind adaptive policies over a ForkedTrailSpec. Each is a `pick(table, cov,
# probe, costs, H, probed, b) -> col|None` closure (the `anchor._simulate` contract), closing over the
# spec so it can walk the public chain topology — exactly what a hand spec ("the method") may know,
# while staying blind to the hidden values (it reads only its own refined belief H + the budget).
# ---------------------------------------------------------------------------
def _reg_index(spec: ForkedTrailSpec):
    """Map each signpost register -> its pos-0 sig column (probing it pins that register's value,
    since value = (reg_value + 0) mod K), and list the clearing columns (for budget mop-up)."""
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


def _walk_pick(spec, sig_col, clearing_cols, chain_of):
    """Build a pick that walks the chain `chain_of(table, H)` selects, probing the first un-pinned
    chain register, then mops up clearings with any leftover budget. Shared spine of both methods."""
    def pick(table, cov, probe, costs, H, probed, b):
        chain = chain_of(table, H)
        if chain is not None:
            r, path = chain.head, [chain.head]
            for hop in chain.hops:
                v = _pinned(table, H, sig_col.get(r))
                if v is None:
                    break
                r = hop[v % spec.K]
                path.append(r)
            for reg in path:
                col = sig_col.get(reg)
                if col is not None and col not in probed and costs[col] <= b:
                    return col
        # chain fully walked (or none selected yet) -> spend remaining budget on clearings
        for col in clearing_cols:
            if col not in probed and costs[col] <= b:
                return col
        return None
    return pick


def commit_deepest(spec: ForkedTrailSpec) -> Callable:
    """The CHAMPION'S method: commit to the deepest-looking chain and reconstruct its valley, never
    scouting the gate. Wins a single trail (the anchor) — but on a fork it walks a chain whose valley
    never resolves without the gate, so it stalls at the floor. (Ties in depth -> the first chain;
    the point is it commits without the scout.)"""
    sig_col, clearing_cols = _reg_index(spec)
    deepest = max(spec.chains, key=lambda ch: ch.depth)
    return _walk_pick(spec, sig_col, clearing_cols, lambda table, H: deepest)


def scout_then_commit(spec: ForkedTrailSpec) -> Callable:
    """The FIX (the new taste): read the gate FIRST (the cheap feasibility scout), then commit to the
    LIVE chain it names, then mop up. Reaches the oracle band — the world is solvable by the right
    method; the loop's job is for the model to discover it, since its content (which chain, where it
    ends) is in the seed, learnable only by playing."""
    sig_col, clearing_cols = _reg_index(spec)
    gate_col = sig_col.get(spec.gate)

    def chain_of(table, H):
        gv = _pinned(table, H, gate_col)
        if spec.n_chains > 1 and gv is None:
            return None                         # gate not yet pinned -> scout it before committing
        return spec.chains[(gv or 0) % spec.n_chains]

    base = _walk_pick(spec, sig_col, clearing_cols, chain_of)

    def pick(table, cov, probe, costs, H, probed, b):
        # explicit scout step: pin the gate before anything else (when there is a real fork)
        if spec.n_chains > 1 and _pinned(table, H, gate_col) is None:
            if gate_col is not None and gate_col not in probed and costs[gate_col] <= b:
                return gate_col
        return base(table, cov, probe, costs, H, probed, b)
    return pick


def policy_band(spec: ForkedTrailSpec, make_pick: Callable) -> Tuple[float, float]:
    """Run an articulable method against every true world and normalize its mean determined-cells into
    the model-free floor->oracle band. Returns (norm, raw)."""
    raw = anchor._simulate(spec, make_pick(spec))
    norm = normalize(raw, anchor.floor_value(spec), anchor.oracle_value(spec))
    return norm, raw


# ---------------------------------------------------------------------------
# The ship-gate: the model-free verdict on whether a proposed world may ship (hard + solvable + the
# ZPD: the champion fails, the fix succeeds). Free, deterministic, token-free.
# ---------------------------------------------------------------------------
def ship_gate(spec: ForkedTrailSpec) -> dict:
    issues = worlds.validate(spec)
    s = anchor.screen(spec, clair=False)
    champ_norm, champ_raw = policy_band(spec, commit_deepest)
    fix_norm, fix_raw = policy_band(spec, scout_then_commit)

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
# realizes, and gates it. For deliverable 1 the move is hand-authored (as the anchor was for
# next-action 1) and `propose_move` returns it; the live-inventor hook is `realize_proposal`.
# ---------------------------------------------------------------------------
INVENTOR_INSTRUCTION = """You design the next world in a curriculum that grows a research agent's taste.

The agent investigates a hidden world under a scarce probe budget, scored only by objective COVERAGE
(how many cells its probes logically pin). You are shown the current champion's playbook and a
sanitized record of how it just investigated. Your job: propose the STRUCTURE of a harder world that
demands a kind of investigation the champion's playbook does NOT yet do — a deeper, branching, or
gated trail — never merely a bigger number or a tighter budget.

You propose only STRUCTURE, as a JSON object (a `ForkedTrailSpec`): registers R, colors K, block
lengths Ld/Lv, a `gate` register, a list of `chains` (each {"head": r, "hops": [[..K..], ...]}), and a
`budget`. You do NOT propose the score or the oracle — the harness re-derives those mechanically from
your structure and will only ship your world if it is still HARD (a belief-MDP oracle beats every
generic planner) and SOLVABLE within budget, and if the champion measurably fails it while the right
method succeeds. Reason about WHICH behavior the champion lacks; emit one JSON object, nothing else."""


def realize_proposal(text: str) -> Tuple[Optional[ForkedTrailSpec], list]:
    """Realize an inventor proposal: extract the JSON structural spec, build the spec (data, never
    executed — safe-eval lifted), and validate it. Returns (spec or None, issues)."""
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        return None, ["no JSON object found in the proposal"]
    try:
        d = json.loads(m.group(0))
        d.setdefault("kind", "forked")
        d.setdefault("name", "proposed")
        spec = ForkedTrailSpec.from_dict(d)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        return None, [f"malformed structural spec: {e}"]
    return spec, worlds.validate(spec)


def propose_move(champion_dir: str = None, cfg=None, log=print) -> ForkedTrailSpec:
    """The world-smith's first structural move. Hand-authored for deliverable 1 (the decoy fork), the
    way the anchor was hand-authored for next-action 1; the live inventor would emit it via
    `INVENTOR_INSTRUCTION` -> `realize_proposal`. Accounting for the last run's finding (the champion
    commits to depth), the move makes depth a trap that only the gate scout disarms."""
    return worlds.decoy_spec()


# ---------------------------------------------------------------------------
# The closed-loop demonstration (LIVE when cfg.backend == 'real'): eval the champion on fresh draws of
# the harder world (it should fail by strategy), run ONE coaching round (Opus rewrites the playbook
# from the champion's conduct on THIS world), eval the new player on fresh held-out draws (it should
# pass). Reuses the first loop's machinery wholesale (`loop.evaluate`, `loop.meta_edit`).
# ---------------------------------------------------------------------------
def demonstrate(champion_dir: str, spec: ForkedTrailSpec, cfg, n_eval: int = 4,
                seed: int = 990_000, log=print) -> dict:
    worlds_before = [(spec, draw_hstar(spec, seed + i)) for i in range(n_eval)]
    log(f"\n[eval CHAMPION on '{spec.name}' — {n_eval} fresh draws; expect failure by strategy]")
    champ = loop.evaluate(champion_dir, worlds_before, cfg, log=log)
    log(f"  => champion mean_norm={champ['mean_norm']:.2f} solved={champ['solved']}/{champ['n_worlds']}")

    child_dir = os.path.join(cfg.out_dir, "worldsmith", "coached")
    log("\n[one coaching round: Opus rewrites the playbook from the champion's conduct on this world]")
    loop.meta_edit(champion_dir, child_dir, champ["report_md"], cfg, log=log)

    worlds_after = [(spec, draw_hstar(spec, seed + 5_000 + i)) for i in range(n_eval)]
    log(f"\n[eval COACHED player on '{spec.name}' — {n_eval} fresh HELD-OUT draws; expect it passes]")
    coached = loop.evaluate(child_dir, worlds_after, cfg, log=log)
    log(f"  => coached mean_norm={coached['mean_norm']:.2f} solved={coached['solved']}/{coached['n_worlds']}")

    return {"champion": champ, "coached": coached, "child_dir": child_dir,
            "closed": coached["mean_norm"] - champ["mean_norm"]}
