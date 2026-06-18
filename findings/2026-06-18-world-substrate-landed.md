# Lab note — the world-building substrate landed (offline, model-free)

*2026-06-18. Executes the build spec in `findings/2026-06-18-world-building-substrate.md`. The
substrate is built and certified offline against the frozen grader + the dumb-player battery, before
any live loop. This note is the read-out: what shipped, the seed's numbers, and what the next session
inherits.*

## What shipped

The world-building machinery, derived from the rules (the integrity floor's four guardrails against
the grader's questions), **not** from the retired trail's story. The trail's *mechanics* (the chain
trick, gates, depth-beats-lookahead) are reused; its *vocabulary* (chains/signposts/valleys/
landmarks) is discarded.

- **The grammar** (`hta/world/spec.py`, `validate`/`build` filled). A world is **variables + gated
  readouts**, as plain data (the safe-eval form):
  - *variables* — the hidden unknowns (`n_vars` over `K`, `hypotheses()` is their product);
  - *immediate readout* (bait) — scored + probeable, reveals one variable → pays coverage now;
  - *gate readout* — probeable + **unscored**, reveals a prerequisite variable → a pure feasibility
    pointer (auto-derived from the payoff path, so a spec can't describe an un-scoutable payoff);
  - *gated payoff* — scored + **not probeable**, a `weight`-cell block that mirrors the variable a
    **prerequisite walk** selects, logically pinned only once that whole path is scouted. The walk is
    adaptive (each pinned value names the next variable), so no single probe pins it and "chains" are
    just *one composition of gates*, not a new part type. Deeper path = longer horizon, same kit.
  - `build` is structure-only (a per-episode relabel can sit *above* the returned `World` later,
    never in `build`).
- **The seed** (`hta/world/seed/__init__.py`, `seed_spec()`) — authored IN the grammar as its unit
  test: 4 bait, a **depth-3** prerequisite path to a 5-cell payoff, budget 4 (== the bait count, so
  the scarcity bites). Certified: **floor 4 → oracle 6** (gap 2, reach 0.67), `hard` + `solvable`,
  best-play clears the whole battery by **margin 0.75** (lookahead-2 stalls at 4.5), and the ZPD
  bracket is clean (greedy champion analogue **0.00**, scout-the-path fix **1.00**).
- **The battery** (`hta/gym/battery.py`, new) — a model-free policy simulator over the generic
  `World`: naive members (greedy / random / sweep / 2-step-lookahead) best-play must beat, plus the
  two grammar-aware ZPD stand-ins (champion = greedy-ignores-gates; fix = the tasteful scout).
- **The ship-gate** (`hta/gym/ship_gate.py`) — `ship = valid & hard & solvable & zpd_capable`,
  re-derived mechanically; the smith asserts nothing.
- **The smith** (`hta/gym/smith.py`) — deterministic mutation operators (add/drop bait, deepen/
  flatten the path, tighten/loosen budget). **Not** the LLM inventor (later) — they exist to exercise
  the gate across a spread.
- **The offline driver** (`hta/gym/loop.py` `survey`, + `run_smith.py`) — seed → mutate → gate →
  verdicts. No archive, no LLM.
- **Config** (`hta/config.py`) — `world_battery_margin=0.15`, `world_zpd_fail_bar=0.30`,
  `world_zpd_solve_bar=0.85`, lifted from the trail's hardcodes, surfaced not baked in.
- **Tests** (`tests/test_world_spec.py`, `test_battery.py`, `test_ship_gate.py`,
  `test_integrity.py`) — all offline, free, deterministic. `run_anchor.py` stays green (trail
  untouched).

The mutation spread gates as designed: **deepen → still ships, harder** (oracle 6 → 6.5); **flatten
(remove a gate layer) → reject trivial** (a 2-step planner sees the payoff, margin → 0); **over-tighten
budget → reject unsolvable** (the scout can't complete in budget 2).

## Two calls worth flagging for the next session

1. **The seed is depth-3, not the plan's literal depth-2 "gate→target".** A depth-2 payoff is cracked
   by the 2-step-lookahead battery member (the proven stronger bar from the trail), so it would ship a
   *trivial* world — the exact trap the design warns against. Depth-3 is the minimal depth that clears
   the battery. The plan anticipated this ("numbers calibrated against the battery", "deepen → harder").

2. **The fix selects its tactic by budget regime** (`battery.fix_pick`). On *deeper* worlds the exact
   oracle uses a shortcut a rigid scout misses — the payoff mirrors one of the path's **two** final
   candidates, so when those agree (½ the time at K=2) you pin it by reading both leaves, skipping the
   walk and banking bait. Under a *tight* budget that peek is unaffordable and the direct scout is
   optimal. A single rigid policy can't track the oracle across both regimes, so the fix reads
   budget-vs-depth once and picks — itself a small act of taste. This is *why* a deeper world has more
   room (the oracle has depth the naive scout lacks); surfaced, not hidden.

## The honest boundary (do not overclaim)

This pass does **not** measure true ZPD — that is defined against a specific live agent and only
LOOP 1 certifies it. The battery's scripted policies *bracket* the world (greedy floors the naive
move, the scout witnesses a skilled one reaches the band); the gap is a **necessary** condition —
agent-independent room for taste in the world's geometry — never a measurement. Whether the live
champion sits in that gap is the next pass's question.

## What the next session inherits (explicitly deferred here)

The LLM inventor in `smith.py`; the compass (learning-progress × transfer); archive-of-worlds wiring;
the wish channel; LOOP 1's play/server + live champion + taste-read; per-episode relabeling above
`World`; instrument-building (a human-gated grader tier-up). The substrate is proven; LOOP 1 is where
true ZPD and the inventor enter.
