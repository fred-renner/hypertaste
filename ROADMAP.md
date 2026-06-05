# Roadmap — growing portable research taste, hands-off

The North Star and the staged path to it. `WORLD_DESIGN.md` is the technical detail of
*today's* world (Chapter 1); this file is where the whole thing is going and why the
staging is the way it is. Read this for direction, `WORLD_DESIGN.md` for the current
mechanics.

## Next action

**Step 1 — first real-backend run: done (2026-06-05).** 3 iterations validated the loop
end-to-end on live `claude -p`. Every child improved (fitness `0.586 → 0.610 → 0.620`), the
held-out transfer world was solved in every iteration (general taste, not curriculum
overfit), and the world-smith built taste-bearing `structures={'exception','regime'}` off
the agent's `weak_tags`. Cost landed exactly at the prediction: **~$1/iter** ($3.00 total,
of which the Opus meta edit is $2.02). The signature result — the meta agent didn't flip a
flag, it wrote **version-space active learning** (a `_splitting_probe` that picks the probe
most evenly splitting the hypotheses still consistent with the evidence), and its own
comment cites the exact failure it was repairing. The machinery works.

Two caveats to carry into scaling: `target_difficulty` held at 2 (correct — the agent isn't
yet *mastering* level 2, so the dial shouldn't climb; the ZPD is doing its job), and one
episode hit `error_max_turns`. With `--n-transfer 1` the transfer signal is still n=1 noisy.

**Step 2 — the ~10–15 iteration run: done (2026-06-05). Honest negative result — the loop
runs but does not climb.** 12 iterations, `$13.98` (cost exactly as predicted ✓), machinery
clean (6/12 children improved, 3 episodes hit `error_max_turns`). But the fitness curve is
**flat with noise, not climb-then-flatten**:

```
0.313 → 0.497 → 0.507 → 0.496 → 0.505 → 0.494 → 0.498 → 0.630 → 0.486 → 0.495 → 0.452 → 0.444
```

One transient spike (gen_0008 = 0.630) that selection never re-exploited; otherwise a
random walk around ~0.50. Root cause is **upstream of the meta agent: the measurement has
almost no dynamic range, so there is no taste gradient to climb.** Three coupled symptoms:

- **The frozen transfer set is a constant.** Of the two held-out worlds, world_0 is solved
  with `agree=1.00` in *every* iteration (trivial) and world_1 is *never* solved by anyone,
  parent or child, gen 0→12 (`agree~0.95`, off the edge the other way). One trivial + one
  impossible = zero between-generation signal. (Step 1's "transfer held!" was this artifact
  at n=1.)
- **The difficulty dial pinned to the floor.** `target_difficulty` dropped 2→1 by iteration
  2 and stayed at 1 for all 12. The agent rarely solves train worlds, so the ZPD has no
  *mastery* to push against and ratchets to the floor — and sits there. The dial moves, but
  only downward.
- **Selection can't compound.** Between-generation fitness differences (~0.49–0.51) are
  inside eval noise (n_train=2, n_transfer=2, single episode each), so the one good jump
  (gen_0008) was never reliably reselected.

**Verdict: do not scale to 30 iterations yet — fix the signal first.** The loop is
optimizing against a near-constant; more iterations just buy more random walk.

**Step 3 — edge-calibration + diagnostics: done (2026-06-05). The measurement is now
honest, and it proves the worlds are still too hard for the task model.** 5 iterations,
`$8.68` (as estimated), `eval_repeats=2`. The three levers shipped: a model-free *edge
classifier* (a falsifier solves the world in budget, a confirm-biased prober does not)
calibrating the frozen transfer set and biasing training worlds; the dial floored at the
edge band; and per-iteration + end-of-run diagnostics that split the signals. The
calibration did its job at the measurement level — the one-trivial + one-impossible transfer
pair is gone — and the diagnostics reveal the truth the step-2 flat curve was hiding:

```
composite fitness : 0.379 → 0.456 → 0.358 → 0.364 → 0.438
solve-rate (all)  : 0.17 → 0.17 → 0.00 → 0.00 → 0.17
transfer-solve    : 0.00 → 0.00 → 0.00 → 0.00 → 0.00   (held-out, every iteration)
info-gain (taste) : 0.35 → 0.38 → 0.35 → 0.34 → 0.37
target_difficulty : 2 (pinned at the floor)
```

The held-out transfer-solve is a clean ZERO across all five iterations — the agent genuinely
does not recover these rules. This **confirms the PI's hypothesis** ("maybe the agent isn't
actually getting better — proven by the heldout set"): it isn't, and now it's visible. Two
coupled causes, both "too hard for THIS model":

- **Calibrated to the wrong agent's edge.** `at_edge` uses an *optimal* falsifier as the
  "good taste" reference, but Haiku-with-good-taste is far weaker than optimal, so every
  edge world sits above Haiku's reach. The real ZPD is *easier* than the optimal-prober edge.
- **The exact-recovery bar is too harsh / agreement is saturated.** Haiku lands `agree~0.9`
  but `solved=0` almost everywhere — consistently *close but not exact*. The 0.50-weight
  `solved` term is all-or-nothing (a weak model rarely flips it) and `agreement` is pinned
  near 0.9 by battery class-imbalance, so neither hands the meta agent a smooth gradient.

The infrastructure (edge classifier, honest diagnostics, faithful mock smart agent) is
correct and stays; the *band* and the *scorer* are what need tuning.

## Next action — Step 4: a gradient the weak model can actually climb

1. **Smooth the fitness gradient (highest leverage).** Replace saturated raw `agreement`
   with *balanced* accuracy (mean of true-case and false-case agreement) so "getting closer"
   registers continuously before exact recovery — a gradient Haiku can climb. Keep `solved`
   (exact empirical equivalence) as the dominant term and the integrity invariant intact.
2. **Calibrate the band to the TASK MODEL, not an optimal prober.** Either weaken the
   reference falsifier toward Haiku's strength, or do a one-time cached measurement of the
   seed model's solve-rate and keep worlds where it sits ~10–40% — real headroom to climb.
3. Re-run 5 iterations; success = a *visible* climb in solve-rate and the held-out transfer
   curve, not composite noise. (Each 5-iter real run is ~$9, so tune, don't scale.)

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
| **1** | deterministic hidden rule `f(x,y,z)→bool` | **exact equivalence** — your rule behaves identically to mine on a fixed battery | falsification, hypothesis decomposition, Occam | **current** |
| **2** | no exact rule — an uncertain/noisy process | **calibration** — how much probability you put on what actually happened | weighing evidence, quantifying uncertainty, knowing what you don't know | future |
| **3+** | worlds you must act on, not just observe | **intervention quality** — the soundness of the experiment you designed | experimental design, controlling confounds, causal reasoning | future |

The principle behind the staircase: **the judge is the most stable thing *within* a
chapter and the most deliberate thing to change *between* chapters.** Worlds and difficulty
self-evolve continuously and untouched; the judge does not move inside a chapter.

## Transitions are the experiment, not an interruption

A chapter change is a **warm-start, not a reset.** What carries across the boundary is the
**agent's accumulated taste** (its strategies, its self-improvement playbook, its lineage);
what resets is the judge and the world substrate. You extract what the student learned and
seed the next chapter with it.

This makes the boundary the **cleanest test of the thesis**: if taste is really general,
an agent that mastered Chapter 1 should enter Chapter 2 with a *head start* even though the
judge is new. If it transfers, taste is real and portable. If it doesn't, what we measured
was game-specific skill wearing taste's clothes — also a finding. Either way the transition
*is* the experiment.

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
2. **First transition, by hand.** Author Chapter 2's judge (calibration). Warm-start the
   agent from Chapter 1's lineage. Headline measurement: **transfer** — did Chapter-1 taste
   give a head start? This is the thesis on the line.
3. **One or two more hand transitions.** Extract the pattern of a healthy transition.
4. **Close the outer loop.** Encode that pattern into the substrate-designer: propose the
   next judge — objective, agent-inaccessible, selected for low-transfer-but-solvable. From
   here the human supervises the constitution, not each judge.

It is **one continuous run at the agent level** — the lineage is never discarded. What
changes over time is not the student restarting but the human climbing out of the loop.
