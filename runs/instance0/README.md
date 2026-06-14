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

The coach read the day-one player's conduct (it kept *diagnosing* outputs then abstaining, scoring
the blind floor) and grew: *"budget to FINISH, not to survey … a fully read table is GUARANTEED full
weight."* On held-out `run1` world_1 the grown playbook then spent 8 probes to fully enumerate a
weight-3 table (24/24), turning −0.016 into +0.146.

## Honest reading — read `findings/2026-06-14-instance0-machine-world.md` first

This is **a tactic, not taste.** "Budget to finish, not to survey" is general; "a fully read table is
guaranteed weight" is a scoring-rubric trick that dies on randomness. The world is a flat
budget-allocation puzzle with no structure to *read*, so allocation is the only habit it can grow.
And this did **not** run the real DGM-H loop (`hta/ch2/loop.py`'s archive + sandboxed agentic
meta-edit): the "coach" was a single text rewrite, and the driver duplicates the existing loop. The
numbers are also noisy (small n, weak Haiku; `run2`'s day-one < bare is one failed episode scored 0).
Kept as a useful record, not a success.

## Reproduce

```bash
python run_instance0.py                       # the free build-screen (gate 1)
python run_instance0.py --backend real --seed 1 --n-holdout 6   # the live inner loop
```

The full per-episode transcripts (probes, scratchpads, submitted models, per-output credit) and both
grown playbooks are in `run1_seed0.json` / `run2_seed1.json`.
