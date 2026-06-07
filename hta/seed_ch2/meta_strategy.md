# Meta-strategy playbook (editable)

This is the meta agent's own procedure for improving the task agent on the Chapter-2
register world (reconstruct M hidden cells under a scarce probe budget; score = coverage).
It is part of the editable program: a meta agent may rewrite this file to improve *how*
future improvements are generated (metacognitive self-modification).

## Stance: grow taste from evidence, don't install it
You are not handed a list of what good research taste is, and you should not invent a fixed
one and pattern-match to it. A failure mode copied from a checklist is the designer's taste
re-installed in the agent — the one thing this system is built to get past. Read the agent's
actual trajectory and outcomes and let them tell you where the investigation was weak *this
time*. The named weakness should be one you can point to in the report, not a label you
brought with you. In particular: the cell formulas are public, but knowing the formulas is not
the same as knowing the strategy — do not assume the fix is to tell the agent the answer.

## How to improve the task agent
1. Read `EVAL_REPORT.md`. For each world, trace what the agent actually did: which cells it
   chose to probe (and which it ignored), what it observed, the reconstruction it submitted,
   and how much coverage that earned (raw, and where it lands in the floor->oracle band).
2. Infer the single most impactful weakness in how it investigates — from the evidence, not
   from a template. Ask: given the public structure and what it had seen, were its probes the
   ones that would let it determine the most cells? Did it spend budget probing cells it could
   already predict, or never gather the observations a buried cell needs? Did its
   reconstruction actually use the structure, or just echo what it probed and guess the rest?
3. Make the smallest *general* change to `solver.py` that would help any agent with that
   weakness — prefer structure (how it allocates probes, tracks what it knows, externalizes a
   model of the registers, decides when to compute the rest deterministically vs. guess) over
   surface wording. Keep the `Solver.run(self, channel, llm) -> list[int]` contract intact and
   do not import world internals. Keep the program short: a shorter program that explains more
   behavior has captured a more general regularity.

## Notes (append what you learn across iterations)
- (none yet)
