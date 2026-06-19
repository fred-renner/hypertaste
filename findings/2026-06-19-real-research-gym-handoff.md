# Lab note — the world is the wrong shape (again): a handoff, not a plan

*2026-06-19. A read-only session: reviewed the world-substrate that landed on
`claude/gallant-wright-mlp0ml`, did a full pass over `history/` + `findings/`, and surfaced why
world-building keeps failing the same way. No code written. This is the handoff — the findings and
the decision taken, deliberately NOT a multi-step plan (planning far ahead was itself part of the
failure this session; see Finding 0).*

## Finding 0 — the meta-trap: don't plan the whole staircase

We tried to write a full forward plan (substrate → grader → gates → smith → loops). It read worse
the longer it got: over-reach disguised as thoroughness — the same "do too much at once" that
scatters progress and clutters the repo. The lesson is **useful increments only.** Direction is
settled below; the next session does ONE thing and stops. Do not re-expand this into a multi-step
spine.

## Finding 1 — the gallant-wright world: clean chassis, wrong world

The engineering is sound and worth keeping: a tight split (frozen generic grader · gym · smith),
the integrity floor held (model-free, safe-eval, the smith never scores), offline tests pass. Not
slop. But the *world* re-derives the retired trail's mechanic — a gated payoff "earned" by walking
a pointer chain — with the nouns filed off. By the project's own verdict that is **a tactic, not
taste** (`findings/2026-06-14-instance0-machine-world.md`): there is no position to read, the move
is deductive pointer-following (no hunches), and the no-inference floor is ~0.67 of the ceiling (a
lazy prober gets two-thirds for free), against the old "no-inference coverage ≈ 0" lock. The
grammar is one-trick; the smith's only move is "deepen the path."

## Finding 2 — why every session sleepwalks into this (the durable lesson)

Four forces, all pointing the same way:

1. **The provable-green gradient.** You can cheaply prove *machinery* correct; you cannot cheaply
   prove *a world demands taste*. So sessions drift toward "the loop turns" — a movable proxy for
   "the loop grows taste." Goodhart on our own goal.
2. **History re-anchoring.** The nearest worked example is the trail and the grader is a
   coverage/allocation scorer, so each session rebuilds the smallest thing that fits the allocation
   anchor (`history/NEXT.md`: "the docs got contaminated by the very world we wanted to plant").
3. **Minimalism misfiring.** "Smallest design that works" is right for machinery and fatal for the
   world — "smallest gradeable world" is below-threshold by construction.
4. **Tastelessness is invisible at build time.** A world only reveals it has no taste when a live
   agent (or Opus) cracks it; the trap-tri chapter proved a model-free gate can pass while the live
   student aces the world in-head.

## Finding 3 — the structural cure already exists, unenforced

`ROADMAP.md` ("earning its keep") wrote the cure: **the threshold gate** — *can Opus or the PI
write the optimal policy in closed form, given full information? If yes, the world is below the
line and any taste-gap is noise.* It was named "the first question of every world" and then never
wired as a hard blocker. Make it one, front-loaded **before** any loop work, and the
provable-green gradient finally points at the right thing.

## Finding 4 — the scorer is the root re-anchor

`history/REPLAN.md`'s sharpest line: a cheap exact best-play oracle over an *enumerable* hypothesis
set is *what makes* the optimal policy writable ("enumerate the consistent shapes, probe where they
disagree, deepest first" — menu-reading, not inquiry). "The exact oracle was never the invariant;
it was an implementation choice wearing the invariant's clothes." The grader on the branch is
exactly that oracle. This is why it has felt "not forward."

## The decision taken this session (PI)

Stop tuning sub-threshold toy worlds — we have shown the loop can turn, and that was the wrong
target. **Reopen the scorer, rebuild the gym, and move toward real research** — the fork
`ROADMAP.md` already demanded ("pay for richer substrate… never tune a sub-threshold toy until the
noise looks positive"). Direction (not a plan):

- The gym = the **skeleton of empirical science**, which `ROADMAP.md` already names as the telos: a
  real black-box system, investigated by **costly experiments**, graded on **predicting behavior
  never observed**.
- This escapes the traps at once: non-enumerable → no exact oracle → no writable policy → above the
  threshold by construction; predicting-the-unseen → the no-inference floor is ~0 *for free*.
- The integrity floor survives the jump: grade **prediction against mechanical ground truth**, not
  the reasoning. **Rich world + dumb scorer** = above-threshold AND clean measurement.
- Start fresh on a new branch. **Mine** `history/` + `findings/` for the hard-won realities; do
  **not** trash them. Keep the genome-agnostic core (archive + sandbox airgap) and the integrity
  floor; `DESIGN.md` §1–§4 (definition, rules of the game, "price it", catalogue) survive. The
  clean chassis on `claude/gallant-wright-mlp0ml` is a reference for the module split, not to fork.

## What the next session does (one increment, then stop)

Settle **what the substrate is** — how "real": a generated-but-rich system that keeps the three
chains (cheap, repeatable, mechanically graded) vs. actual code / a simulator — and **how the
threshold gate is mechanized** (a strong solver that must *fail* to max the world). Then prove
**one hand-authored instance clears the threshold gate**, offline, before any episode, smith, or
loop. If it can't clear the gate, fix the substrate, not the loop.

Do NOT: build the loop, author a toy to "get something turning," or write another long forward
plan. Nothing downstream until one instance is real and above the line.
