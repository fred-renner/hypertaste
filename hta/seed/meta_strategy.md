# Meta-strategy playbook (editable)

This is the meta agent's own procedure for improving the task agent. It is part of the
editable program: a meta agent may rewrite this file to improve *how* future
improvements are generated (metacognitive self-modification).

## Stance: grow taste from evidence, don't install it
You are not handed a list of what good research taste is, and you should not invent a
fixed one and pattern-match to it. A failure mode copied from a checklist is the
designer's taste re-installed in the agent — the one thing this system is built to get
past. Read the agent's actual trajectory and outcomes and let them tell you where the
inquiry was weak *this time*. The named weakness should be one you can point to in the
report, not a label you brought with you.

## How to improve the task agent
1. Read `EVAL_REPORT.md`. For each world, trace what the agent actually did: which
   cases it tested, what it observed, what it concluded, and what the outcome metrics
   say about whether its choices reduced its uncertainty or wasted the budget.
2. Infer the single most impactful weakness in how it investigates — from the evidence,
   not from a template. Ask: given what it had seen, was the next move the one that
   would have told it the most? Where did it spend budget without learning?
3. Make the smallest *general* change to `solver.py` that would help any agent with that
   weakness — prefer structure (how it allocates probes, tracks what it knows, decides
   when to stop) over surface wording. Keep the `Solver.run(self, channel, llm)`
   contract intact and do not import world internals. Keep the program short: a shorter
   program that explains more behavior has captured a more general regularity.

## Notes (append what you learn across iterations)
- (none yet)
