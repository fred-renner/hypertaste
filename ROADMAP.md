# Roadmap — growing portable research taste, hands-off

The North Star and the staged path to it. `RESET_DESIGN.md` is the technical detail of
*today's* world (Chapter 2, post-reset); this file is where the whole thing is going and why the
staging is the way it is. Read this for direction, `RESET_DESIGN.md` for the current mechanics,
`NOTEBOOK.md` for the Chapter-2 lab history.

## Where we are — Chapter 1 ran, and it told us the world is the wrong shape

Three real-backend runs (3, 12, then 5 iterations; ~$1/iter, Opus-meta-dominated)
validated the machinery end-to-end: the loop runs, episodes are concurrent, lineage
compounds, cost is as predicted. **But fitness does not climb** — across every run it
random-walks around a floor, and on a calibrated 5-iteration run the **held-out solve-rate
was a clean zero for all five iterations**. The agent is not actually getting better at the
task, and the honest held-out exam proves it.

The essence of *why* (this is the finding to carry forward):

- **The world is a binary oracle.** "Discover the hidden rule" scores by *exact* equivalence:
  you recover the rule or you get nothing. For a weak task model (Haiku) that's ~always
  "nothing" on any taste-bearing world, so the selection signal is flat.
- **The partial-credit patch is hollow.** To fake a gradient, fitness blends in `agreement`
  (fraction of a fixed ~750-point battery matched) + bonuses. But the battery is mostly
  "False", so a lazy guess scores ~0.9 agreement for free; `novelty`/`occam` add more free
  floor. Result: fitness hovers ~0.4 regardless of whether anything was solved — motion
  without meaning.
- **Calibrating difficulty didn't save it.** Tuning worlds to a *reference* prober's edge
  (a falsifier beats a confirm-prober) overshot, because that reference is far stronger than
  Haiku. Calibrating to the real student needs measuring the student, not a proxy.

Net: patching the *scorer* of a binary rule-guessing world is rearranging deck chairs. The
session's edge-calibration code was reverted as a dead-end; only this finding is kept.

## Chapter 2 — the investigation-map (designed; build the thin slice next)

> **Update — superseded by the reset (`RESET_DESIGN.md`).** This section is the *origin* of
> Chapter 2 and the reasoning still holds, but two later findings moved it on: the tape slice
> (a *prompt* is not the unit) and the register/trap-tetra harness (a *code* harness lets the
> meta agent write the oracle → below threshold). The reset's answer: the evolved unit is a
> **non-executable English playbook**, the **model orchestrates** (not Python), and the world
> (the **anchor trail world**) is built so the policy's *content* is learnable only by playing.
> Read `RESET_DESIGN.md`; the full slice-by-slice history is in `NOTEBOOK.md`.

The pivot (PI): stop scoring a binary answer and bolting taste-metrics onto it. Build a
**navigable investigation-map** — a hidden, deterministic, grammar-generated graph the agent
probes under a **scarce budget** — and let fitness be simply **how much of the structure it
uncovered**. Then info-gain, falsification, decomposition aren't side-bonuses; they're the
behaviors that **unlock coverage**. Taste becomes the thing that wins the game.

The design is settled and lives in `NOTEBOOK.md` (archived). The spine:

- **Judge = information-weighted coverage**, normalized by a **model-free DP oracle** on the
  fixed graph (region value = how much it reveals about the *rest* of the grammar, so
  maximizing coverage *is* predict-the-unseen inference). Deterministic, cheap, ungameable —
  the integrity floor is intact, only the function is richer than equivalence. *The
  determinism the floor demands is the same property that yields a computable oracle.*
- **What grows = the allocator** — the multi-drive meta-policy (exploit toward the goal /
  drop everything to chase an anomaly / consolidate). **Deception** (novelty anti-correlated
  with value where it counts) is what makes coverage **discriminate** taste from a
  brute-force walk. Taste is *instrumentally* optimal, never a score-term.
- **Small, dense, deceptive worlds** — value is ambiguity-per-decision, not node count. A
  **propose/expand split** (Opus proposes a compact grammar spec; a fuel-bounded stdlib
  expander realizes it) keeps generation from exploding and near-free in tokens; a
  **taste-gap gate** admits only worlds where a model-free oracle ≫ greedy/random.
- **The science:** one loop; a **frozen ruler** (vanilla Haiku) gates worlds so held-out
  climb = discovery by construction; **MDL on the agent program** as the generality prior;
  **stay-Haiku** as a fixed control; cross-model port as a periodic generality check. The
  taste-prompt is an instrument (gate + bar), **never a target**.

**The thin de-risking slice ran — and is now closed** (`NOTEBOOK.md` → "First/Second/Third
slice", "The rethink"; built in `hta/ch2/`). Two empirical bets gated it: (1) the taste-gap must
be **realizable by Haiku**, not just present in the world; (2) inference must be a **ramp, not a
cliff**. **Bet 2 PASSES** structurally (R²=1.0 — independent segments make coverage linear in the
fraction inferred). **Bet 1's *easy* version FAILS, and that is the finding:** across three slices
we learned to steer the gap's *sign* by world design (transparent-flat → concentrated-negative →
distributed-positive), but once the instrument was made honest (realizable-ceiling normalizer,
generous turn budget, norm-of-mean) **no prompt — tactical or general — lifted a fixed weak model
off the no-inference floor.** The slice did its job cheaply: it falsified *a prompt is the unit of
taste* before a cent on the loop.

Two consequences carry forward. **(a) The unit is a program/scaffold, not a prompt** — the loop
must search scaffold-space (how the agent allocates probes, externalizes notes, decides when to
stop), which is what Chapter 1's `meta-agent-on-program` already was and the slice's prompt-A/B
regressed away from. **(b) The binding constraint is the *threshold*, not difficulty or the
instrument** — both are now honest, yet the signal is still noise, because the tape-world sits
**below the line** where taste has tacit room to matter (Opus can write its optimal policy in five
lines; the mock solver nearly is it). The next session answers the **threshold question** directly
(see "earning its keep" below), not another tuning cycle. The substrate (tape + coverage judge +
DP oracle) and the three-plane skeleton are sound; what was wrong was measuring a tacit-taste gap
in a world that has none.

## The thesis

`hypertaste` is a bet that **research taste is a real, portable, learnable thing** — and
that a system can grow it in itself, recursively, with a human progressively stepping out
of the way. "Taste" = the instincts that separate good inquiry from lazy inquiry:
hunting for the case that falsifies you (not the one that confirms you), decomposing a
hypothesis, knowing what you don't know, designing the experiment that isolates the
variable. If those instincts are real, they **transfer** across very different problems.
That portability is the whole claim, and the system is built to prove or refute it.

## The two loops

```
INNER loop (automated, hands-off):  worlds self-evolve to the student's edge
OUTER loop (human now → automated):  judges change between chapters as taste saturates
```

- **Inner loop — the difficulty dial.** Within a chapter, the world-smith continuously
  tunes puzzle difficulty to sit *right at the student's edge* (solvable with effort, not
  trivially, not never). No human number. This is the self-calibrating, smooth dial; see
  "The smooth dial" below for what's built vs. not.
- **Outer loop — the judge.** A chapter has one fixed, objective judge. When the student
  saturates a chapter (taste stops climbing on the held-out test), the *kind of question
  the world asks* changes, which forces a **new judge**. Today a human authors that
  transition; the endgame automates it (see "Closing the outer loop").

## Chapters — a staircase of judges, each forcing a new research virtue

The substrate grows by **changing the judge**, not by making numbers bigger. Each judge is
an *objective, mechanical principle* (never an LLM opinion), and each is chosen because it
makes a **new research virtue** necessary to win:

| Chapter | World kind | Judge (objective principle) | Virtue it forces | Status |
|---|---|---|---|---|
| **1** | deterministic hidden rule `f(x,y,z)→bool` | **exact equivalence** — your rule behaves identically to mine on a fixed battery | falsification, hypothesis decomposition, Occam | done — pivoted (binary oracle → flat signal) |
| **2** | navigable hidden **investigation-map** (the anchor → forked trail worlds) | **coverage** — how much of the structure you uncovered under a scarce budget | budget allocation, value-of-information, reading global structure, predict-the-unseen | **current — English playbook, model-orchestrated; agent loop ran (held-out 0.50→1.00); the world-smith (second loop) is built — it evolves the world's *structure* and ships only in the ZPD; live closed-loop demo next (`RESET_DESIGN.md`)** |
| **3** | no exact rule — an uncertain/noisy process | **calibration** — how much probability you put on what actually happened | weighing evidence, quantifying uncertainty, knowing what you don't know | future |
| **4+** | worlds you must act on, not just observe | **intervention quality** — the soundness of the experiment you designed | experimental design, controlling confounds, causal reasoning | future |

The principle behind the staircase: **the judge is the most stable thing *within* a
chapter and the most deliberate thing to change *between* chapters.** Worlds and difficulty
self-evolve continuously and untouched; the judge does not move inside a chapter.

## Transitions are the experiment, not an interruption

A chapter change is a **warm-start, not a reset.** What carries across the boundary is the
**agent's accumulated taste** (its strategies, its self-improvement playbook, its lineage);
what resets is the judge and the world substrate. You extract what the student learned and
seed the next chapter with it.

This makes the boundary the **cleanest test of the thesis**: if taste is really general,
an agent that mastered one chapter should enter the next with a *head start* even though the
judge is new. If it transfers, taste is real and portable. If it doesn't, what we measured
was game-specific skill wearing taste's clothes — also a finding. Either way the transition
*is* the experiment.

**Exception — Chapter 1 → 2 is started fresh.** Chapter 1's fitness never climbed (binary
oracle → flat signal), so there is no accumulated taste to warm-start from. We therefore
treat Chapter 2 as a fresh start and measure climb-from-zero against a frozen ruler; the
warm-start/transfer test above lands at the *first transition out of a chapter that actually
produced taste* (Chapter 2 → 3 onward).

## The smooth dial (within a chapter)

The dial is smooth when difficulty is a **continuous, measurable quantity** the smith
hill-climbs against the *live* student — not a staggered ladder of named levels. Three
design moves make it so:

1. **Continuous difficulty** — roughly, *how much the rule takes to describe* and *how many
   sharp probes it takes to crack* — so "a bit harder" is infinitely fine-grained, not a
   jump between integer levels.
2. **Calibrate to the live student** — the smith keeps puzzles the *current* student solves
   only ~half the time, with effort. The edge is then defined by the student and moves on
   its own. No human difficulty knob.
3. **Uncapped composition** — let puzzles compose without an artificial depth ceiling, so
   the substrate doesn't run out of "a little harder" for a long time and the climb feels
   open-ended.

Guardrail: a smith told only "make it hard" can cheat with dumb hardness (bigger numbers,
unsolvable traps). The search target must be **hard in the taste sense** — worlds where the
lazy confirm-it strategy fails and only the go-find-the-counterexample instinct wins.

**Status today.** This smooth-dial work is **deferred to a chapter that produces climbing
taste**: Chapter 1 (the numeric pipeline that had a difficulty escalator) was retired for a flat
signal, and Chapter 2's first job is to clear the *threshold* (a world where taste has tacit room)
before its difficulty is worth auto-calibrating. Calibrate-to-live-student returns at "Wire +
calibrate" on the anchor world (`RESET_DESIGN.md`).

## Closing the outer loop

The endgame automates the judge transition without ever letting the system grade itself
softer. The move is the trick already in play — the world-smith is allowed to be creative
*because the agent is scored by an objective function the smith doesn't control* — lifted
one level up:

- Introduce a **substrate-designer** role that proposes the next world-kind **and its
  objective judge**, under two iron constraints: the judge must be **mechanical, not an
  opinion**, and the agent must **never be able to edit it**.
- Give the designer a mechanical objective: a new chapter is valuable exactly when the
  current agent's taste **transfers poorly** to it (headroom to learn) **while still being
  solvable in principle** (not noise). Same learning-progress logic as the inner loop,
  lifted to the chapter level.

Then the loop is genuinely closed and recursive: the inner loop finds the student's edge,
the outer loop opens a new chapter when the student saturates the old one, and the human's
role **rises in altitude** — from authoring each judge to authoring the *space of legal
judges* and the integrity constraints.

## The integrity floor (the one thing that stays human)

The agent can **never** be allowed to rewrite its own judge. The student (and the
self-improving meta agent) is optimized *against* the score; if it could move the score, it
would "grow taste" on paper by making the test easier — reward hacking, not research. So:

> Everything self-evolves **except** the constitution that judges must be **objective and
> agent-inaccessible.** That constitution is the irreducible human contribution.

This is not a limitation to engineer away — it is the axiom that makes the whole system
science instead of a machine learning to lie to itself. **99% hands-off is the prize; 100%
is wireheading.** You get out of the way of the *content*; you remain the author of the
*rules of the game*. The existing airgap and the objective-not-LLM judge already encode
this floor; every future chapter inherits it.

## Why start cheap (the game is the instrument, not the toy)

We deliberately start on the cheapest substrate — the number-rule game — and reach for real
research later, for an **epistemic** reason, not timidity. You can only tell whether the
system grows *taste* if you can *measure* taste cleanly, and clean measurement needs
objective, cheap grading. Real-research worlds have noisy, expensive, contestable grading;
start there and you can't distinguish "it works" from "the metric is mush." Proving the
mechanism cheaply — *taste self-evolves and survives one judge change* — is exactly the
result that turns "reach real research" from a science risk into a scaling question.

**Design invariant this imposes today:** build every interface as if real research is
coming, so a new chapter is an *addition*, never a redesign. This is why the world/agent
airgap, the objective-judge separation, and the narrow probe channel matter now, while the
world is still a toy.

## Is the harness earning its keep? (the null, the threshold)

The honest challenge to the whole project: you can **hand-design** a plausibly-tasteful
researcher today — an allocator, an interestingness signal, a playful-exploration drive —
and just install it. If that's competitive, the co-evolution is theater. So name the null,
the line that beats it, and how we'll know which side of the line we're on.

- **The null is a smart spec.** A hand-authored agent is *taste frozen at the ceiling of
  what the designer could articulate the day they wrote it.* It has one fatal tell: it
  **cannot certify itself** — no integrity floor, so it declares victory by construction.
  The apparatus's product was never the agent; it is *the non-movable measure plus a
  curriculum that keeps finding the edge.* The agent is almost incidental.
- **The threshold: taste must become tacit.** The loop only beats the spec where the right
  allocation policy is **found by playing, not deducible by inspecting** — where neither the
  PI nor Opus can derive it in closed form from the world source. Below that line the harness
  is scaffolding and a smart hand-design is competitive; above it, the loop is the only way
  up, because it climbs past *any* designer's articulable ceiling, Opus's included. If a
  tasteful policy could simply be *written down*, taste would be articulable and the thesis
  (taste is the tacit residue) would be false.
- **Why "Opus can diagnose the fix" is not a refutation.** Diagnosing taste ≠ possessing it.
  Opus prescribes the world-fix *from outside* — post-hoc, full-information, seeing the rule
  and the oracle, under no budget. The task agent must *enact* taste *from inside* — blind to
  the rule, under budget, in the moment. The coach who reads your footwork can't return the
  serve; the diagnostic vantage is precisely the one the player never has. *Corollary for
  closing the loop:* a smith that designs **around** the agent's weakness is collusion —
  Goodhart at the curriculum level. The only legal coupling is the **ZPD via an objective
  gap** (fail-now-but-learnable on the non-movable scorer), never the agent's internals.
- **We are honestly below the line — the slice measured it, not a failure.** At Chapter-1/2
  complexity Opus-the-coach sees the whole board, so a hand prompt is competitive and the loop
  is not yet earning its keep. The Chapter-2 slice **confirmed this the expensive-but-decisive
  way**: a careful, budget-matched hand prompt could *not* beat vanilla on a deceptive,
  distributed-value world once the instrument was honest. Per the falsification condition above,
  the suspect is therefore no longer the world's difficulty or the instrument — both were made
  honest — but the **threshold itself**: there is no world *yet* where taste has tacit room to
  matter. A hand-designed researcher could never tell you that; this one is built to.
- **The threshold is now an operational gate, not a footnote.** Make it the first question of
  every world/chapter: *can Opus (or the PI) write the optimal allocation policy in closed form,
  given full information — the rule, the oracle, no budget?* If yes, the world is **below the
  line**: a hand spec is competitive, the loop cannot climb past an articulable ceiling, and any
  taste-gap you measure is noise (exactly the slice's reading). Only a world where the answer is
  **no** — the policy is found by playing, not deducible by inspection — can the loop earn its
  keep. This gate is "earning its keep" lifted into a build decision: it screens *worlds and
  chapters* the way the taste-gap gate screens individual worlds. The standing tension it forces
  is real and must be chosen deliberately, not dodged: **"start cheap"** wants a world simple
  enough to grade objectively, while **this gate** wants one complex enough that Opus can't solve
  it on paper — and the cheapest such world may not be cheap. Resolve it by picking the side
  on purpose (pay for richer substrate, or scope early chapters to plumbing-validation and move
  the taste claim later), never by tuning a sub-threshold toy until the noise looks positive.

## The gym and its chains — why taste, why this world (drafted 2026-06-11, PI reread pending; preserve through every docs collapse)

**Why taste is the right thing to grow.** Capability is the abundant resource: the labs pour
billions into it, and it arrives — from this project's perspective — free and forever
improving. What does not arrive is the judgment layer that converts capability into progress:
which question to ask next, what to ignore, when to check, when to stop, when to quit. Watch
an agent fail a long task: it is almost never "couldn't make the move" — it is "made the
wrong move, confidently." Taste is that layer. Its positive form is **allocation**: spending
the next probe, hour, or unit of belief where it buys the most. Five faces of one skill:
direction (not getting lost), the next-move call, attention (noticing the anomaly that
matters), belief management (how sure am I, really), and exit judgment (commit, abandon, or
find the way around). A grown procedure compounds in a way capability spending doesn't: it
ports onto every better engine that ships.

**The three chains, accepted on purpose.** (1) The grader must be dumb and mechanical — never
an LLM judge, or the agent learns to please the judge. This rules out grading real research
directly. (2) Episodes must be cheap and repeatable thousands of times. (3) The winning
strategy must not fit on an executable napkin, or a hand prompt ties the grown playbook and
the loop is theater. Inside those chains, the planted machine — hidden structure, scarce
probes, graded on predicting behavior never observed — is the skeleton of empirical science:
nature is a black box, experiments cost, and theories are graded on prediction. Long horizons
stay in reach (length scales cheaply in-gym); *real* is the chain, and the port is the bridge.

**The honest boundary, named so it is never silently claimed.** Not in the gym yet: taste in
choosing problems over years, and taste in inventing new concepts and representations.
Problem choice gets its first step with the discoverable goal menu; concept invention arrives
only at the port or with a truly open-ended smith. Instrument-making — build the meter you
weren't given — *is* in the gym, late and ratified.

**The compass.** Evolution never installed curiosity; it built environments where poking the
surprising thing paid on average, and selection wrote the disposition in. The catalog
(PLAN.md, record v2) is that move used deliberately: each human inquiry disposition names the
world feature that makes it pay. It steers the smith and validates the loop — did selection
rediscover these unprompted? — and it never touches the score, the seed, or any agent-side
surface.

**The thermometers.** The transfer bet is monitored, not assumed: an alien family the smith
never touches, a planted bug in real code, and the vocabulary watch — all read-only to
selection. The port is the meet; the gym is the gym.

## The staged plan

The manual early chapters are **how we earn the right to automate the outer loop** — you
cannot write the substrate-designer correctly until you've watched a couple of judge-changes
by hand and seen what a *healthy* transition (taste carries, headroom appears) looks like
versus a reset (everything collapses).

1. **Chapter 1 (now) — prove the inner loop.** Taste self-evolves to the student's edge on
   deterministic rules; held-out taste climbs, then flattens. Success criterion: that flat
   line. (Build the smooth dial: continuous difficulty, calibrate-to-live-student, uncapped
   composition.)
2. **First transition, by hand (now).** Author Chapter 2's judge (**coverage** on the
   investigation-map). Start **fresh** — Chapter 1 never climbed, so there is no taste to
   warm-start from; the headline measurement is whether **held-out coverage climbs from a
   fresh start above the frozen ruler** (vanilla Haiku). *Status: reset (`RESET_DESIGN.md`).*
   The judge + oracle + substrate are built and the **ramp** holds; the slice and the
   trap-tetra harness then taught the two corrections now locked in: (i) the world must clear
   the **threshold gate** — the anchor trail world does (oracle ≫ heuristic, allocation not
   inference, so no closed-form solver); and (ii) the taste carrier is a **non-executable English
   playbook** the meta agent evolves — *not* a program/scaffold (a code harness let the meta agent
   compile the oracle and slide back below threshold). The warm-start *transfer* test — does
   mastering one chapter give a head
   start in the next — becomes meaningful at the *next* transition, once a chapter actually
   produces climbing taste to carry.
3. **One or two more hand transitions.** Extract the pattern of a healthy transition
   (taste carries, headroom appears) vs. a reset.
4. **Close the outer loop.** Encode that pattern into the substrate-designer: propose the
   next judge — objective, agent-inaccessible, selected for low-transfer-but-solvable. From
   here the human supervises the constitution, not each judge.

It is **one continuous run at the agent level** — the lineage is never discarded. What
changes over time is not the student restarting but the human climbing out of the loop.
