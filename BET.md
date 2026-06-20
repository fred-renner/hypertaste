# BET — the cheapest test of the whole idea

> **Status: the next move.** Before any more machinery, run the smallest experiment that can
> confirm or kill the core bet. This file fixes *what we're testing and why*; the *how* (which
> benchmark, what the agent is, how the framing is injected) is left open for a brainstorming
> session. North star: `VISION.md`. Detailed second layer: `DESIGN.md`.

## The two things in our head — and why they point the same way

There are two projects tangled together:

1. **The science** — *what is taste, operationalized?* What are the actual rules of good judgment
   once you stop hand-waving and write them down.
2. **The bet** — that taste has the shape `Value(X) ≈ LP · transfer / cost, biased to uncertainty`,
   run by a goal-weighted allocator. This is a hypothesis about the structure of taste, not a fact.

The resolution: **the cheapest version of the experiment serves both, and the heavy loop serves
neither yet.** You learn more about what taste *is* by hand-writing the framing into an agent and
watching what transfers than by debugging a world-smith — because the manual loop puts you
face-to-face with the content of taste every round. The smith, the archive, the airgap, the world
language are all *automation of a manual process we have not yet run once by hand*. You don't
automate a loop before you've made one part on the bench.

## The experiment, in one line

**Equip a cheap agent with our framing; race it against the same cheap agent without it, on an
existing benchmark where the path matters; measure the lift.**

- **Equipped agent** — a Haiku Claude Code agent given the framing (the `LP · transfer / cost`
  reading, the goal-weighted allocator) as its playbook / operating instructions.
- **Baseline agent** — the same Haiku Claude Code agent, plain, no framing.
- **The arena** — an *existing* benchmark, borrowed not built. This is the one hard part we can't
  skip (see "The one constraint").
- **The measurement** — the **port lift**: does *equipped* beat *plain* on held-out tasks. This is
  the verdict. Reading the agent's behaviour/notes in plain English for taste is *color*, not the
  verdict — plain-English taste advice is cheap and self-deceiving on its own.

## What it answers

- **Is the bet real?** Does the `LP · transfer / cost` framing actually buy better judgment, or is
  it a label that changes nothing.
- **What is taste, operationalized?** What the framing has to become — in concrete agent
  instructions — to move the needle is itself the operational definition we're after.
- **Does it port?** The framing is text; the whole long-horizon thesis is that such text carries
  taste onto a weak model. A cheap model is the honest place to test that — a strong one may already
  have the reading and hide the lift.

## What "all of taste" means here (scope ambition, not v1)

The functional is only the **evaluator** slice — *choosing among moves that are already in front of
you*. We want all of taste, so two more halves are named now so v1 doesn't quietly mistake itself
for the whole:

- **The generator** — *coming up with the right moves in the first place*, upstream of the
  evaluator and arguably the more taste-laden half. The functional is silent on it. We want it.
- **In-context learning (the organism feels the cost, fast)** — humans grow taste because the
  organism feels the bite *mid-run* and revises its read on the spot, not because evolution slowly
  rewrites a playbook across lifetimes. The lever: make the **within-episode** loop the place
  learning happens — the agent revising its own reading mid-run from what just bit it — rather than
  (or before) a slow cross-episode playbook rewrite. This is the more faithful model of
  "taste developed by exposure to failure." Held as a real design fork to fold in, not v1's first
  cut.

## The one constraint we can't skip

Most existing benchmarks grade the **answer, not the path** — which is the "transfer is a hop"
failure wearing a leaderboard. The benchmark must be one where **the path matters and value is
un-guessable**: agentic / interactive (debugging a real system, a multi-step task/web agent, a
game, a discovery sim), **never QA**. Choosing that benchmark *is* the world-building question —
but borrowing a good one is far cheaper than authoring a world language, and it hands us better
scoring and a better world for free.

## Why not the loop (yet)

This is the smallest thing that can kill or confirm the bet, in days not months. If equipped beats
plain by a real margin on a path-benchmark, *then* the loop (smith, archive, airgap) is worth
building — to automate and scale the playbook discovery we just did by hand. If it doesn't lift
even hand-tuned, no amount of loop machinery saves it.

## Open — for the next session to brainstorm

Settled above: the bet, the framing, the port-lift verdict, the path-not-answer constraint, the
"all of taste" ambitions. Left open, deliberately:

1. **Which benchmark.** Concrete candidates that are path-mattering and cheap to run; how held-out
   is drawn; what counts as a win margin.
2. **What the agent is.** Exactly how the framing is injected (system prompt / playbook /
   scaffold), what "equipped with taste" concretely reads as, how to keep equipped vs plain a fair
   A/B (same model, same tools, only the framing differs).
3. **How to measure the lift cleanly.** Enough runs that luck washes out; abstain/honesty handling;
   guarding against the framing just being "try harder" rather than "read the position."
4. **How much generator / in-context learning to attempt in v1** vs. deferring to a later cut.
