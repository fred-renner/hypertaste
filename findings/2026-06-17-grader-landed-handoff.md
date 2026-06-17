# 2026-06-17 — Grader landed; handoff for the first real world

## State

The grader is done and on `main`: `hta/lab/scoring.py` (+ `tests/test_scoring.py`, 74 tests
green; thresholds in `hta/config.py`). It is the shared substrate of both loops — one machine,
two uses:

- `oracle(world)` / `floor(world)` set the band (best-play ceiling, lazy-play bottom).
- `score_run(world, run)` places a player's run in that band, 0 = lazy, 1 = oracle (LOOP 1).
- `grade_world(world, cfg)` rates a world's difficulty: gap + reachability (LOOP 2's ship-gate).

It rides a small `World` Protocol at the top of `scoring.py` and never looks inside a
hypothesis, so it is generic and model-free by the import graph.

## Your job this session: the world, not the player loop

Build `hta/world/spec.py` — the spec format, `validate`, and the deterministic `build` — and
author + certify the **first real world** under `hta/world/seed/`. Skip `dgmh/play/` and
everything downstream of it. The binding constraint right now is *a world worth climbing*, not
the player loop: the trail proved the loop runs — its failure was the world.

> This supersedes the step order in `findings/2026-06-17-scaffold-rewrite-tree.md` (which lists
> `dgmh/play/` next). World first; the player spine waits until there's a world to climb.

## The bar that matters (read before porting anything)

Do **not** mechanically clone `hta/_trail/worlds.py`. The first world must be one where the gap
between best-play and lazy-play *is taste* — the score climbs only by **reading the position to
choose the informative probe next**, not by a fixed formula or a single repeated tactic (that
tactic-not-taste collapse is the instance-0 failure we reset over; see
`findings/2026-06-14-instance0-machine-world.md`).

Certify it ships with `grade_world`: a wide `oracle`−`floor` gap (skill matters) **and** the top
reachable in budget (solvable). Port the trail's *structural* ideas if useful, but **drop its
value law entirely** — that law now lives in the world's `observe`, never in the grader. The
trail tangle (value law baked into the grader) was the tell; keeping it out is the cut.

## The contract `build` must satisfy

`build(spec, *, seed)` returns something implementing the `World` Protocol in `scoring.py`:

- a `budget: int` attribute, and six methods: `hypotheses()`, `positions()`, `cost(p)`,
  `observe(p, h)`, `probeable(p)`, `scored(p)`.
- **Positions are identified by their index in `positions()` order** — that index is the `col` a
  run logs and submits. The grader assumes this; the world must honor it.
- `observe(position, hypothesis)` returns an **int**; the engine only ever compares these for
  equality (to split the candidate set and to decide when a cell is pinned). It is a pure lookup
  — "what would I see here if `h` were true" — never a solve.

## Two hard constraints, easy to trip

1. **Size it so the exact oracle stays computable.** `oracle` is exact value iteration over
   belief states (subsets of the surviving hypothesis set). Keep the hypothesis space small and
   enumerable, or it will not terminate. "Deterministic so the oracle is computable" is an
   invariant, not a nicety.
2. **`world/` stays model-free and safe-eval.** No `hta.llm` import anywhere under `world/`. A
   spec is data: `validate` it, then `build` expands it — never import or execute it. The hidden
   answer `build` draws from `seed` is held harness-side only; it never reaches a player's tool
   surface.

## Deferred — don't build speculatively

- `dgmh/play/` and the rest of the LOOP-1 spine; all of `gym/` (the automated smith search).
- The richer hardness check in `grade_world` (oracle must beat a *greedy* planner, not just the
  lazy floor) — add it when the ship-gate genuinely needs more than the band-level verdict.
- `hta/_trail/` stays untouched and green until the fresh lab carries its own end-to-end tests.
