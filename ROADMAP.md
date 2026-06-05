# Roadmap — growing portable research taste, hands-off

The North Star and the staged path to it. `WORLD_DESIGN.md` is the technical detail of
*today's* world (Chapter 1); this file is where the whole thing is going and why the
staging is the way it is. Read this for direction, `WORLD_DESIGN.md` for the current
mechanics.

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

The pivot (PI): stop scoring a binary answer and bolting taste-metrics onto it. Build a
**navigable investigation-map** — a hidden, deterministic, grammar-generated graph the agent
probes under a **scarce budget** — and let fitness be simply **how much of the structure it
uncovered**. Then info-gain, falsification, decomposition aren't side-bonuses; they're the
behaviors that **unlock coverage**. Taste becomes the thing that wins the game.

The design is settled and lives in `WORLD_DESIGN.md`. The spine:

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

**The thin de-risking slice ran** (`WORLD_DESIGN.md` → "First slice"; built in `hta/ch2/`).
Two empirical bets gate everything: (1) the taste-gap must be **realizable by Haiku**, not
just present in the world; (2) inference must be a **ramp, not a cliff** (partial grammar →
partial coverage). Result: **bet 2 PASSES** (R²=1.0 — independent segments make coverage
linear in the fraction inferred), but **bet 1 does not yet** — and the failure inverts
Chapter 1's. Haiku infers the grammar *fine*; the world is just **too transparent** (a bare
prompt already sits at normalized 0.61 of the floor→oracle band, the ceiling is low, and the
+0.05 taste edge drowns in Haiku noise). Chapter 1 overshot difficulty too *hard*; this
slice overshot too *easy*. **Next: add deception** (hide segment boundaries, lure probes onto
flashy dead-ends, stepping-stones) to open Haiku-realizable headroom, **denoise** with
repeats, then re-gate before building the loop. The substrate (tape + coverage judge + DP
oracle) and the three-plane skeleton it reuses are sound.

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
| **2** | navigable hidden **investigation-map** (grammar-generated graph) | **coverage** — how much of the structure you uncovered under a scarce budget | budget allocation, value-of-information, reading global structure, predict-the-unseen | **current — slice ran: bet 2 (ramp) holds, bet 1 (gap) needs deception** |
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

**Status today.** Chapter 1 has the objective judge (exact equivalence), a held-out
transfer test, a solvability gate, and a difficulty escalator — but the escalator steps a
coarse integer from a fixed cold start (`hta/loop.py:_target_difficulty`), and composition
is capped at the `exception` shape (`hta/world/grammar.py`). The three moves above —
continuous difficulty, calibrate-to-live-student, uncapped composition — are the next
within-Chapter-1 work. See `WORLD_DESIGN.md`.

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
   fresh start above the frozen ruler** (vanilla Haiku). *Slice status:* the judge + DP
   oracle + substrate are built and the **ramp** holds, but the first hand-built maps are
   too transparent — vanilla Haiku is already near-tasteful, so there is no realizable gap to
   climb yet. The open work is **deception** (make the naive move wrong) before the loop. The
   warm-start *transfer* test — does mastering one chapter give a head start in the next —
   becomes meaningful at the *next* transition, once a chapter actually produces climbing
   taste to carry.
3. **One or two more hand transitions.** Extract the pattern of a healthy transition
   (taste carries, headroom appears) vs. a reset.
4. **Close the outer loop.** Encode that pattern into the substrate-designer: propose the
   next judge — objective, agent-inaccessible, selected for low-transfer-but-solvable. From
   here the human supervises the constitution, not each judge.

It is **one continuous run at the agent level** — the lineage is never discarded. What
changes over time is not the student restarting but the human climbing out of the loop.
