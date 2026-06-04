# Handoff

Current status of `hypertaste`. For architecture/run instructions see `README.md`; for
how the world grows see `WORLD_DESIGN.md`; for what we borrow see `REFERENCE.md`. Older
TODO-1/2/3 narratives live in git history and `runs/` — not repeated here.

## Where we are

The full DGM-H pipeline works end-to-end on the live backend. The first three TODOs
(first real run, world-growth design + first slice, containerized airgap) are all done.

**Verified by a 5-iteration real run** (`runs/run5_2026-06-04.log`, 2026-06-04):
- Runs clean for 5 iterations, no crashes; airgap held (no rule leaked).
- **Real rule recovery**: 6 worlds solved exactly (agreement 1.00), incl. held-out transfer.
- **Lineage compounds**: weighted parent selection latched onto `gen_0002`; 3/5 children
  improved over their parent. ZPD difficulty reacts (eased 2→1 when the agent struggled).
- Cost $6.41 / 40 calls. Breakdown: meta agent (Opus) **77%**, world-smith + Haiku
  episodes 23%. The meta agent is the cost center; single-session already squeezed the
  task agent to ~12%.

## Speed/efficiency pass (2026-06-04, after run5)

The run5 wall-clock (~30 min/5 iter) and a ~13% spurious-failure rate were diagnosed and
fixed:
- **Root cause of "episode error"**: `error_max_turns` — the chatty Haiku agent ran out of
  *turns* before its *probes*. Fixed: turn budget is now `max_probes*2 + buffer` (probes
  bind, not turns) + a tightened episode prompt (probe on turn 1, no `remaining()`, no
  prose). A non-solver that uses all its probes is now a legitimate worst-score failure
  (worlds are gated solvable-in-budget), not a rescued one.
- **Biggest speed win**: per-world eval now runs episodes **concurrently**
  (`eval_concurrency`, default 4) — they were independent subprocesses run serially.
  Measured A/B (3 real episodes): **85.3s serial → 34.2s concurrent (2.5×), same cost.**
- Removed a ~3s/call stdin stall (`stdin=DEVNULL` on every claude launch).
- Consolidated the two launchers onto one shared arg parser; dropped the redundant
  `scripts/real_eval_demo.py`.
- Validated by a 1-iteration real run (`runs/smoke_after_2026-06-04.log`): 0 episode
  errors, transfer world solved exactly, child IMPROVED (+0.0475).

## The bottleneck now: the Opus meta agent

With concurrent eval, a real iteration is ~6 min and the **meta-agent edit is ~4–5 min of
it** (and ~77% of cost). It is now *the* lever for both speed and money — eval and the task
agent are no longer where the time goes. Options, cheapest first:

1. **Lower `meta_max_turns`** — observed 14–27 turns against a 40 budget; ~28 is safe and
   each Opus turn is ~15s of wall-clock.
2. **Diagnose-from-sampled-failure** (deferred in `REFERENCE.md`): hand the meta agent one
   sampled failing trajectory instead of the full sanitized report — smaller per-turn
   context (the agentic claude -p re-reads context each turn) and a sharper signal.
3. **Staged-eval gating** (deferred): eval a child on 1 world first, full set only if it
   clears a bar — the cheapest way to add `eval_repeats > 1` variance damping without
   multiplying episode cost.

**Docker airgap**: parked. Code + tests exist (`hta/sandbox.py`, `tests/test_sandbox.py`)
but the in-container claude call was never run live (Docker Hub rate-limit here). Revisit
only when a hard boundary is actually needed; soft airgap (`--sandbox none`) is the default.
