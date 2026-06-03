# Meta-strategy playbook (editable)

This is the meta agent's own procedure for improving the task agent. It is part of
the editable program: a meta agent may rewrite this file to improve *how* future
improvements are generated (metacognitive self-modification).

## How to improve the task agent
1. Read `EVAL_REPORT.md`. For each world, look at the probe trajectory, the booleans
   observed, the final guess, and the taste metrics.
2. Diagnose the dominant failure of *research taste*:
   - **Confirmation bias**: probes keep confirming (mostly True) instead of trying to
     falsify. Fix by proposing diverse / boundary / edge-case probes.
   - **Doom loop / repeats**: `reuse_rate` high or repeated trajectory. Fix by tracking
     `seen` probes and forcing novelty.
   - **Weak space reduction**: `avg_info_gain` low. Fix by choosing probes that split
     the remaining hypotheses roughly in half.
   - **Over-complex guesses**: `occam` low, `agreement` high but `solved` False. Fix by
     guessing the simplest rule consistent with the evidence.
3. Make the single most impactful edit to `solver.py`. Keep the `Solver.run(self,
   channel, llm)` contract intact and do not import world internals.

## Knobs available in the seed
- `STRATEGY = "naive" | "smart"`: a coarse switch from confirmation-biased to
  falsification + Occam behavior. Flipping it is the cheapest first improvement; deeper
  improvements rewrite the probing/guessing logic itself (e.g., maintain an explicit
  hypothesis set and pick maximally-splitting probes).

## Notes (append what you learn across iterations)
- (none yet)
