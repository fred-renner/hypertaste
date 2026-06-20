# BET — the cheapest test of the whole idea

> **Status: scoped, arena chosen.** The smallest experiment that can confirm or kill the core bet.
> The arena (DiscoveryWorld) and the experiment design (harness fixed, toggle the allocator) are
> now settled, and so is the taste principle the equipped arm runs; what's still open is the
> playbook's *exact prose* and the run protocol. North star:
> `VISION.md`. Detailed second layer: `DESIGN.md`.

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

**Equip a cheap agent with our framing; race it against the same agent without it, on DiscoveryWorld
where the path itself is scored; measure the lift.**

- **Equipped (toggle-on)** — a Haiku Claude Code agent whose move/goal selection runs under the
  allocator discipline (`LP · transfer / cost`, goal-spawning, biased to uncertainty).
- **Baseline (toggle-off)** — the *same* agent, *same* harness, selecting by Haiku's default under a
  world-general "you are a researcher under uncertainty; solve X."
- **The arena** — DiscoveryWorld, borrowed not built (see "Settled: the arena").
- **The measurement** — the **port lift**: does toggle-on beat toggle-off on held-out task
  variations. Reading the agent's notes in plain English for taste is *color*, not the verdict —
  plain-English taste advice is cheap and self-deceiving on its own.

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
  evaluator and arguably the more taste-laden half. The functional is silent on it. Deferred,
  named.
- **In-context learning (the organism feels the cost, fast)** — humans grow taste because the
  organism feels the bite *mid-run* and revises its read on the spot, not because evolution slowly
  rewrites a playbook across lifetimes. **DiscoveryWorld pushes back mid-episode, so v1 already
  lives in this regime:** you act, the world answers, the agent revises its read on the spot from
  what the experiment returned. What stays deferred is the slower *cross-episode* playbook rewrite —
  which is exactly LOOP 1.

## The one constraint we can't skip

Most existing benchmarks grade the **answer, not the path** — which is the "transfer is a hop"
failure wearing a leaderboard. The real test is not *what gets scored* but **whether the answer is
guessable without playing the path**: outcome-scoring on an un-guessable answer is fine — it's the
cleanest *agent-inaccessible* score we can get. The benchmark must be agentic / interactive, with
the goal many linked moves away and reality pushing back along the way — **never QA**. DiscoveryWorld
satisfies this, and goes one better: it scores the path *directly* (see below).

## Settled: the arena — DiscoveryWorld

DiscoveryWorld (Ai2, 2024) — an interactive, text-based scientific-discovery simulator: 8 fields,
120 tasks, 3 difficulty tiers, ~20k-line Python sim with an agent API. It clears every bar:

- **Knowledge-seeking science, not code.** The episode *is* the discovery cycle — hypothesize,
  design an experiment, run it, read the result, revise. The value function as a task, not a label.
  (Code was the thing to avoid: every agent is trained on it, and it's not the general-research
  target.)
- **Reality pushes back, mid-episode.** You act; the world answers. "Learning while running" is
  *forced by the world*, not bolted on — and the LLM failure we most care about (chasing
  interesting-sounding noise because nothing corrects you) is exactly what it measures resistance to.
- **Not hard in the reasoning sense.** ~4th-grade science; the difficulty is *what to do next*, not
  raw smarts — precisely the target.
- **Mechanical scoring, and one metric grades the path.** Three automatic metrics — task completion,
  *task-relevant actions taken*, explanatory-knowledge correctness; **no LLM judge** (the integrity
  floor holds). The middle one grades whether you did the *right things*, so the path-vs-answer
  tension dissolves — it's a mechanical *path* score.
- **Held-out for free, and un-memorizable.** Every task has parametric variations (data, solution,
  layout change each run) — the held-out split is built in, and "all agents are trained on this"
  can't bite.
- **Cheap and drivable.** Text sim + agent API → a native Haiku Claude Code agent driving it through
  a *confined action interface* (the airgap: the agent acts only through probes, never reads the
  world source). This *is* "spawn local agents limited in what they can do."

**Rejected — ARC-AGI-3:** shape-perfect (no instructions, acquire goals on the fly, build a world
model, learn continuously) but **floor-fatal** — frontier models score <1%, humans ~100%, so a
cheap model lands at zero either way and there is no lift to measure; also abstract grids, not
knowledge-seeking. **ScienceWorld** is the cheaper warm-up if the adapter fights us, but it's
procedure-following more than discovery (lower taste-fidelity).

**A note on reach:** DiscoveryWorld isn't just a test fixture — it's a credible *real* world for the
framework. Finding it **collapses the roadmap**: with a fixed, taste-demanding, path-scored world in
hand, LOOP 2 (the world-smith) is unnecessary for now. The whole program reduces to LOOP 1 — grow
the agent against this world.

## Settled: the experiment — harness fixed, toggle the allocator

The unit under test is the **allocation policy** (when to make which move), not prose. So:

- **Hold the harness fixed; toggle the allocator.** Same multiturn scaffold, same memory management,
  same subexplorer-spawning in both arms. The *only* difference is whether move/goal selection runs
  under the allocator discipline. This isolates *taste* from *engineering hygiene* — memory and
  subagents help regardless of taste, so they stay constant. **Two arms, not three.** (Almost
  evolutionary: one mutation, measured.)
- **The playbook stays world-general — a discipline, not an arm.** Write it once for "a researcher
  under uncertainty," never naming DiscoveryWorld. If it lifts, it's taste; the instant you tune it
  to the benchmark, you're measuring overfitting. This is the answer to "the comparison goes
  apples-to-oranges": don't let it.
- **The v1 gate is the honest minimum: does the allocator framing lift a dumb model at all** —
  toggle-on > toggle-off, world-general, on held-out variations. The stronger "beats a generic
  try-hard prompt" check (did the value-*reading* help, or just the extra deliberation?) is a **v2
  arm** — named so we don't fool ourselves, not the first gate. One variable at a time.

The **genome** — what's evolvable — is the whole Claude Code harness within constraints: the
playbook, the memory policy, the subexplorer config. *Anything that helps a Claude Code agent, within
some constraints.* Toggling it by hand now is a **hand-run of DGM-H LOOP 1**; once the hand-run shows
lift and names the genome, the same knobs plug straight into the automated loop.

## Settled: the taste principle — the operating loop

This is the toggle-on arm's *content*. The functional is the **snapshot** (*what to value*); the
principle turns it into *what to do next* and folds in self-correction:

**Value the position → forecast the move out loud → act → revise on the surprise.** Before each move
the agent commits to a one-line prediction — *what I expect to learn, what it opens toward the goal,
what it costs* — then acts, then treats the **gap between forecast and result** as the signal. That
one loop carries all of it: LP (*what will I learn*), transfer (*what it opens*), cost,
uncertainty-bias (*forecast where you're least sure*), **and** learning-while-running — the surprise
is the bite the organism feels. A model that never predicts can't be surprised, so nothing corrects
it: that *is* the core failure mode, restated.

Two **guards**, each aimed at one named failure:

- **The transfer gate, with an explicit play goal.** A move must serve *some* live goal to count;
  novelty with zero transfer to *any* goal dies — the antidote to *getting lost in
  interesting-sounding stuff*. But the portfolio always carries a small, weight-limited **play goal**
  whose only notion of worth is "is this teaching me something," so genuinely interesting orphan
  threads — **stepping stones** — survive on the play component instead of being culled. When a
  stepping stone turns out to wire into the main goal, the agent **spawns a new subgoal** that now
  carries real transfer weight. (The gate kills noise; the play goal keeps live curiosity; promotion
  is how a sidequest graduates.)
- **The discriminating-move habit.** Prefer the experiment whose result you *can't* predict and that
  *splits* your live hypotheses — *seek the bite*. The anti-pattern is the confirmatory experiment
  that teaches nothing.

**Learning-while-running is both clocks.** *Fast:* the forecast-gap feeds back into the *next*
allocation within the episode — the prediction is acted on, not just stated. *Slow:* the *tools for
how* the agent forecasts, gates, and revises are themselves part of the evolvable genome and sharpen
across episodes (LOOP 1). The within-episode loop is the most taste-laden and most fragile part to
get right — and it's also why a loop could work at all: the machinery is self-correcting by
construction.

## Why not the loop (yet) — hand-run first, then LOOP 1

Even though DiscoveryWorld is a real world and tempts us straight into LOOP 1 (let the loop grow
whatever harness maximizes the task-relevant-actions metric), we run it **by hand first**. You don't
automate a search before you've done it once: the hand-run is cheap, it tells us the lift exists at
all, and it names the genome the loop would search over. *Then* LOOP 1 is the clean scaling step —
against a fixed world, with LOOP 2 retired. If hand-tuned doesn't lift, no loop machinery saves it.

## Open — for this session to resolve

Settled: the bet, the arena (DiscoveryWorld), the experiment design (harness-fixed toggle, world-
general playbook, lift-exists gate), the taste principle (the forecast-act-revise loop + two guards),
the hand-run-then-LOOP-1 sequencing. Left open:

1. **The playbook's exact prose.** The operating loop and the two guards are settled (above); what
   remains is the *smallest wording* that actually induces them in a Haiku agent, and how structured
   the forecast must be — free-text, or a fixed *expect / opens / cost* line. Found on the bench, not
   by argument.
2. **The difficulty band.** Is DiscoveryWorld too easy — does a *tasteless* agent also solve it,
   leaving no gap? Pick the tier where plain-Haiku scores low-but-nonzero; lean on the
   task-relevant-actions metric, which separates tasteful from flailing play even on completed tasks.
3. **The confined action interface.** Exactly what moves the agent can make (design/run an
   experiment, read an instrument, take notes, spawn a subexplorer, revise hypotheses) and how the
   airgap is enforced.
4. **The run protocol.** How many task-variation runs to wash out luck; what counts as a win margin;
   abstain/honesty handling.
5. **Generator + the v2 purity arm** — deferred, named so v1 doesn't mistake itself for the whole.
