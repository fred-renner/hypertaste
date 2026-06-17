# 2026-06-17-3iter-real — three live LOOP-1 iterations on instance 0

Generated 2026-06-17 by:

```bash
python run_lab.py loop --iterations 3 --backend real --eval-repeats 2 --out-dir outputs/run-3iter
```

Real backend (live Haiku episodes through the probe-MCP airgap + live Opus meta-edits). Started
from branch `claude/dazzling-franklin-xwgkzm` (the fresh-lab build, Pass 2). Cost: **$4.15** over
**39 `claude -p` calls** (36 task episodes + 3 Opus edits).

**The question this run asked:** over three iterations, does *taste* (band-normalized coverage on
instance 0) climb as Opus rewrites the agent's playbook? **Answer: not cleanly in the score** —
the signal is dominated by world-draw variance at 3 worlds/eval, and the per-iteration progression
is confounded (each iteration draws *different* worlds). But the *disposition* Opus grew is the
right one and visibly refines across the lineage. Full write-up:
`findings/2026-06-17-3iter-real-taste.md`.

## The numbers

Fair comparison (parent vs. child on the **same** worlds, within an iteration):

| iter | parent → child | parent fit | child fit | Δ | child held-out |
|------|----------------|-----------:|----------:|-----:|---------------:|
| 1 | gen_0000 → gen_0001 | 0.589 | 0.500 | −0.089 | 0.50 |
| 2 | gen_0000 → gen_0002 | 0.107 | 0.322 | **+0.215** | 0.50 |
| 3 | gen_0002 → gen_0003 | 0.482 | 0.464 | −0.018 | **0.71** |

One of three edits improved the agent on a fair (same-worlds) comparison. The seed (gen_0000) itself
scored 0.589 / 0.107 on iterations 1 / 2's draws — a swing wider than any edit's effect, which is the
crux: **draw variance > edit signal** at this world count.

## The lineage (the disposition Opus grew, trajectory-only, never told "taste")

- `gen_0000` (seed) — generic "spend your budget well."
- `gen_0001` — deferred payoffs are **all-or-nothing**: count the full unlock-cost before the first
  probe; never strand budget halfway down a sequence.
- `gen_0002` — harvest the immediate-pay clearings first; *the biggest-looking region is the gated
  one — don't let its size pull your early probes*; separate probed/forced cells from guesses.
- `gen_0003` — **reverses gen_0002**: do *not* grab the cheap cells first; **reserve** the deep
  region's probes up front and fund it FIRST, then fill leftovers with clearings — "its block of
  probes must be set aside before you start spending, never scavenged from the remainder."

That gen_0002→gen_0003 reversal is Opus self-correcting toward the genuinely better allocation
(reserve capacity for the high-yield job) — the scout-then-commit move instance 0 plants.

## Files

- `archive/gen_XXXX/` — the lineage: each node's `playbook.md` (the evolved English), `node.json`
  (fitness summary), and the sanitized `EVAL_REPORT.md` its meta-edit saw.
- `iter_XXXX.json` — per-iteration audit: spec, the hidden draws, parent/child evals with **full
  episode transcripts**. Replayable via `loop.score_result(spec, hstar, result)`.
- `run.json` — invocation args, per-iteration outcomes, `claude -p` call/cost accounting.
