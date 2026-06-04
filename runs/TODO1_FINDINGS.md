# TODO 1 — First end-to-end real evolution run (analysis)

**Date:** 2026-06-03 · **Log:** [`todo1_2026-06-03.log`](todo1_2026-06-03.log)

**Command**
```bash
python run_loop.py --iterations 3 --backend real --episode-mode single_session \
  --max-probes 8 --n-train 2 --n-transfer 2 --meta-max-turns 12
```
Real `claude -p` throughout: Haiku task agent (single-session episodes via the
stdio-MCP probe tool), Opus meta agent (agentic self-modify), Opus world-smith.

## Bottom line
The real pipeline runs **end-to-end across 3 iterations with no crashes**, the archive
grew with **4 valid nodes** (seed `gen_0000` + 3 children), and the **airgap held**
(no hidden-rule name/source appears in any `EVAL_REPORT.md` handed to the meta agent).
The Opus meta agent makes **substantial, sensible research-taste edits** — well beyond
the mock's one-line strategy flip. But **fitness did not climb** over the run, for
reasons that are now well understood (truncated meta edits, no cumulative lineage,
noisy 4-world fitness). Cost landed exactly in the predicted band: **$2.47 / 30 calls**.

## Numbers
| iter | curriculum | parent `gen_0000` | child | Δ | verdict |
|---|---|---|---|---|---|
| 1 | diff 2, no weak tags | 0.7576 (solved 3/4) | `gen_0001` 0.6093 (2/4) | −0.148 | regressed |
| 2 | diff 2, weak=[sign_zero, arithmetic] | 0.4284 (1/4) | `gen_0002` 0.4646 (1/4) | **+0.036** | **improved** |
| 3 | diff 2, weak=[sign_zero, arithmetic] | 0.5754 (2/4) | `gen_0003` 0.5527 (2/4) | −0.023 | ~flat |

Child-fitness progression: **0.609 → 0.465 → 0.553**. Best stepping stone: `gen_0001` (0.6093).

**Transfer fitness** (the real generalization signal — the frozen suite `all_equal`,
`sum_eq` is identical every iteration, so it's directly comparable):
`gen_0001` 0.613 → `gen_0002` 0.616 → `gen_0003` 0.508. **Flat, then down — taste did
not generalize upward in this run.** (All three children solved the easy `all_equal` and
missed `sum_eq`; the dip in `gen_0003` is the transfer `sum_eq` agreement collapsing to 0.)

LLM calls: 30 — `world_smith`:3, `task_episode`:24, `meta`:3. **est_cost ≈ $2.47.**
Per-call: Haiku episode ≈ $0.04–0.05; Opus meta agentic ≈ $0.42–0.58 (the cost driver).

## What the Opus meta agent actually did (the headline finding)
Asked whether it edits `solver.py` "in non-trivial ways beyond the strategy flip" — a
clear **yes**. All three children (`solver.py` grew 131L → 182/214/215L) **independently
and convergently invented the same two mechanisms**:

1. **Falsification-by-design.** A hardcoded, deterministic battery of maximally-diverse
   probes (`[2,4,6]`, `[6,4,2]`, `[1,1,1]`, `[2,4,8]`, `[-3,0,3]`, …) spent before
   handing off to the LLM — so good experimental design **does not depend on the weak
   Haiku model resisting confirmation bias**. The agent's own comment: *"so research
   taste does not depend on the model resisting confirmation bias."*
2. **Verified Occam induction.** A complexity-ordered candidate-rule library + a
   consistency check against the observed booleans; it returns the **simplest rule
   consistent with all evidence**, only deferring to the LLM's free-form guess when that
   guess is *also* fully consistent. `gen_0001` additionally injects the simplest
   consistent candidate into the guess prompt as a hint.

This is real taste engineering, and its convergence across three independent edits shows
it's robust, not luck. It never touched `episode_prompt.md` or `meta_strategy.md`
(it ran out of turns first — see below), so the metacognitive surface stayed at seed.

## Why fitness didn't rise (and what to change)
1. **The meta agent runs out of turns every time.** `turns=13, error=True` in all three
   iterations (budget was `--meta-max-turns 12`). The Read→diagnose→Edit loop does not
   fit in 12 turns, so edits are applied (under `acceptEdits`) but the agent is cut off
   mid-revision — as likely to leave a half-finished change as a clean win.
   **→ Bump `meta_max_turns` to ~25–40 for real runs** (the handoff flagged the analogous
   episode-buffer risk; same root cause here).
2. **No cumulative lineage.** `select_parent` (random over valid parents, RNG seeded by
   the iteration index) picked the **seed `gen_0000` all three times**. Every child is
   "seed + one edit," so improvements can't compound — exactly the multi-generation
   accumulation TODO 1 wanted to observe never got a chance. **→ For evolution runs,
   bias parent selection toward the current best / recent children** (REFERENCE.md's
   `score×novelty` selection is the deferred fix), or at least seed the RNG so lineage
   advances.
3. **Noisy fitness over only 4 worlds + stochastic Haiku.** Parent `gen_0000` scored
   0.76 / 0.43 / 0.58 across iterations *as the same program* — the swing is driven by
   the regenerated training curriculum (2/2 → 0/2 → 1/2 solved) and Haiku's run-to-run
   variance, not by the agent. A genuinely-better child can still lose on 4 noisy worlds.
   **→ More worlds per eval and/or repeated episodes would shrink the variance** (cost
   permitting); staged-eval gating (REFERENCE.md) would keep it affordable.

## Loop mechanics that DID work
- **Weak-tag targeting closes the loop:** iterations 2–3 targeted `gen_0001`'s weak modes
  (`sign_zero`, `arithmetic`), and those worlds were materially harder for the seed agent
  (train solved dropped 2/2 → 0/2). The world-smith is steering at the agent's blind spots.
- **single_session economics held:** 24 Haiku episodes for ~$1 total; the Opus calls
  dominate cost, as expected.
- **Invalid-child handling was never triggered** — all three children stayed valid
  `Solver` programs despite the truncated edits.

## ZPD note
Difficulty stayed at **2** for the whole run: escalation needs the best agent to solve
≥75% of a curriculum, and it never did (best `gen_0001` solved 2/4). Escalation will only
show up once a child is strong enough — which (1) and (2) above are prerequisites for.

## Follow-ups applied (2026-06-04)
All three "what to change" fixes above are now in code (tests in `tests/test_pipeline.py`):
1. **Meta turn budget** — `meta_max_turns` default raised 30→40 (`hta/config.py`).
2. **Cumulative lineage** — `select_parent` defaults to **weighted** quality×novelty
   selection (`hta/archive.py`, the `score_child_prop` shape): the over-branched seed is
   damped toward ~1% while the fittest fresh child dominates, so lineage compounds.
   `--parent-selection random` restores the prior uniform policy.
3. **Variance** — new `eval_repeats` knob (`--eval-repeats N`) re-runs each world's episode
   N times and averages the taste metrics (majority-vote on `solved`). Default 1 leaves the
   mock pipeline byte-for-byte unchanged.
See `HANDOFF.md` for the next-run command that exercises all three.
