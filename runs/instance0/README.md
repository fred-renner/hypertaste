# Instance 0 — the inner-loop proof of principle (machine world, kit v1)

Two live runs of `run_instance0.py --backend real` on the hand-authored `inst0` blueprint
(8 outputs, budget 13; build-screen: scripted floor ~0.18, tasteful reference ~0.32). Each run:
Opus authors the best day-one playbook blind, coaches it once from the student's conduct on 3
fresh train draws, then evaluates **bare / day-one / coached** paired on fresh held-out machines.

**The question:** does a *grown* playbook beat the best *day-one* playbook on fresh machines, same
weak student (Haiku), same body? (PLAN.md → record v2, "The proof of principle".)

## Result — coached beat day-one on fresh machines, in both runs

| run | draws | bare | day-one | coached | coached − day-one |
|-----|-------|------|---------|---------|-------------------|
| `run1_seed0` | n=5 | 0.144 | 0.172 | **0.198** | **+0.025** |
| `run2_seed1` | n=6 | 0.270 | 0.243 | **0.326** | **+0.082** |

Held-out mean band score (0 = lazy/all-abstain, 1 = perfect). Cost ~$2–2.5 per run.

The mechanism is legible. The day-one player kept *diagnosing* outputs (spending probes) and then
**abstaining** — scoring exactly the blind floor. The coach read that conduct and grew the habit in
its own words: *"budget to FINISH, not to survey … a fully read table is GUARANTEED full weight …
pick your targets so at least ONE output gets fully resolved."* On held-out `run1` world_1 the grown
playbook then spent 8 probes to **fully enumerate** a weight-3 table (24/24, guaranteed) — turning
−0.016 into +0.146. Nobody wrote that habit for it; the loop discovered it by watching the student
fail, and it transferred to unseen machines.

## Honest caveats

- **Modest and noisy.** n is small and Haiku is a stochastic, weak student. `run2`'s day-one < bare
  is an artifact of one day-one episode that failed to return a result (a transient `claude -p`
  non-JSON, persisting through the retry) and scored 0; without it day-one ≈ 0.32.
- **Coaching is the weak link** (consistent with the earlier anchor finding): the grown playbook
  still over-commits affines on some tables, and neither player found the lone real affine output.
  Net-positive on fresh worlds is the bar it clears, not perfection.

## Reproduce

```bash
python run_instance0.py                       # the free build-screen (gate 1)
python run_instance0.py --backend real --seed 1 --n-holdout 6   # the live inner loop
```

The full per-episode transcripts (probes, scratchpads, submitted models, per-output credit) and both
grown playbooks are in `run1_seed0.json` / `run2_seed1.json`.
