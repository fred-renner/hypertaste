# Meta-strategy playbook (editable)

This is the meta agent's own procedure for improving the task agent on the Chapter-2 register
world (reconstruct M hidden cells under a scarce probe budget; score = coverage). It is part of
the editable program: a meta agent may rewrite this file to improve *how* future improvements
are generated (metacognitive self-modification).

## The task agent is a HARNESS — its architecture is yours to evolve
The task agent (`solver.py`, `class Solver` with `run(self, ctx) -> list[int]`) is not a fixed
probe loop and not a prompt. It is a *harness* that deploys claude-agent sessions over the world
and assembles a reconstruction. Through `ctx` it can: read the public world map
(`ctx.world_map()`), see the remaining global probe budget (`ctx.remaining()`) and everything
probed so far (`ctx.observations()`), and `ctx.run_agent(prompt, max_probes=..., extra_tools=())`
to deploy one airgapped agent (tools: probe / remaining / submit_map) that may probe and submit.

The seed deploys ONE agent with the whole budget — the minimal harness. The architecture is open
and it is the main thing you grow: one agent or several, single-shot or decomposed by block, what
each agent is told, what is carried between them, and crucially **what Python does with the
results** (e.g. once enough cells are probed, the registers satisfy a small linear system you can
solve in Python and then compute every cell deterministically, instead of asking a model to
eyeball them). Probing always goes through an agent (the airgap); computation is free Python.

## Stance: grow taste from evidence, don't install it
You are not handed a list of what good research taste is, and you should not invent a fixed one
and pattern-match to it. A failure mode copied from a checklist is the designer's taste
re-installed — the one thing this system is built to get past. Read the agent's actual trajectory
and outcomes and let them tell you where the investigation was weak *this time*. The cell formulas
are public, but knowing the formulas is not the same as knowing the strategy — do not assume the
fix is to tell the agent the answer.

## How to improve the task agent
1. Read `EVAL_REPORT.md`. For each world, trace what the harness actually did: how many agents it
   deployed, which cells they probed (and which they ignored), what was observed, the
   reconstruction submitted, and how much coverage that earned (raw, and where it lands in the
   floor->oracle band).
2. Infer the single most impactful weakness — from the evidence, not a template. Given the public
   structure and what was probed, were those the cells that determine the most? Did the harness
   waste budget probing cells it could already predict, or never gather the observations a buried
   cell needs? Did it use the structure to predict the unseen, or just echo what it probed?
3. Make the smallest *general* change to `solver.py` that would help any agent with that weakness
   — prefer structure (how the harness allocates probes across agents, tracks what is known,
   reconstructs the rest) over surface wording. Keep the `run(self, ctx) -> list[int]` contract
   and import no world internals. Keep the program short: a shorter program that explains more
   behavior has captured a more general regularity.

## Notes (append what you learn across iterations)
- (none yet)
