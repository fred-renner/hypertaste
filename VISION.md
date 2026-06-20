# VISION — what taste is, and why it has to be grown

> **Status: the north star.** The core framing the whole project is built to serve — what taste is,
> what a world must be to demand it, and what grows vs. what we fix. It supersedes the *framing* in
> `DESIGN.md`; the machinery there (the rules of the game, "don't prove it, price it", the
> catalogue, the smith, the wish channel) still stands as the detailed second layer.

## The definition

**Taste is choosing your next move well by reading your position.**

The reading has a shape. The value of a position is what you *forecast* you'd learn by going there
(**learning-progress**), times how far that learning carries toward your goal (**transfer**), per
unit cost — and when you're unsure, bet on what you're least sure of.

`Value(X) ≈ learning-progress(X) · transfer(X → goal) / cost`, biased to uncertainty.

Three things this line *absorbs*, so it isn't misread:

- **It is forecasts all the way down — there is no "immediate" term.** You never *collect* value at a
  position; you predict what's learnable, predict what it opens, and spend a little to test the
  prediction (sometimes the forecast is trivial, so you don't even spend that). Taste is just the
  *quality of those forecasts*.
- **`transfer` is the value function in disguise, not a closeness-to-goal number.** It is the
  downstream, multi-horizon worth of everything the move *opens*, weighted toward your goals — so the
  depth ("a position's worth is mostly what it opens") and the planning both live inside this one
  term. The "goal" is a **portfolio** (a vector, one component per live goal); how you collapse the
  vector is still open (see the portfolio section).
- **"Biased to uncertainty" is only weakly here.** The learning term already leans toward what you
  don't yet know, but the sharp, non-myopic version — betting *across horizons* on what you're least
  sure of — is **grown, not written**. The crude line does not give it for free.

That sentence is the *label*. It is not the skill — and that gap is the whole reason the project
exists (see "Why it has to be grown").

## The three layers — only one is fixed

Everything that has confused us comes from collapsing these. Keep them apart:

1. **The score** — predict behaviour you never observed, graded by a dumb mechanical function the
   agent can't touch. *This is the only fixed point.* It can't move, ever; moving it is
   reward-hacking. But the score is the **selection pressure, not the measurement of success**: it
   can't tell grown taste from a good-enough imitation of perfect play. The measurement is the
   **port lift** — does the weak model *plus the playbook* beat the weak model *alone* on held-out
   worlds. The score selects; the port lift judges.
2. **The functional** — `LP · transfer / cost, biased to uncertainty`. This is **not** ground
   truth. It's our crude, hand-written estimator — a guess at what good play looks like, written by
   thinking. It's a *lens* and a *seed*, not a target: it gets the agent off the ground and is the
   prior the grown estimator (layer 3) is **meant to outgrow**. It is sharpened only by us — but we
   do not pour effort into perfecting it, because polishing the part that's meant to be crude is just
   overfitting the lens. The leverage is in the world and the playbook, not the formula.
3. **The grown estimator** — the playbook (position → move, in the agent's own words) plus the way
   the agent runs its goals. This is what the loop discovers, and it is *meant to surpass* layer 2.

The tell that layer 2 isn't truth: "biased to uncertainty" is plainly an *estimator move* — a
trick for estimating value well, not part of what value *is*. The whole functional is
estimator-level. That is why it is improvable, and why nothing optimizes against it.

## Seed the world, grow the estimator

We never write the skill into the agent's head. We build the *world* so that reading the position
well is the only way to win — and let selection grow the reading.

This is the resolution to "do we seed taste or grow it?" Both, at different addresses:

- We **seed the world** — its structure *is* the functional made un-computable.
- The agent **grows the estimator** — the actual reading of an uncomputable position, which is
  taste, and which we never had to give it.

What went wrong before was never "we forgot to seed taste." Our *worlds* were flat and computable,
so reading the position wasn't the winning move, so the thing that grew was a tactic. Fix the
world, not the agent.

## Why it has to be grown (not just written down)

The functional is five words; the estimator is enormous. "Maximise your win probability" is the
entire functional of chess — known since 1950. The function from a board to its win probability is
a galaxy-sized object no one can write, and AlphaZero only built it by playing itself millions of
times. The label was never the bottleneck; the object was. Taste is the same shape: we can write
the label, we cannot write the object.

Two independent reasons, either one sufficient:

- **It's too big and tacit to write.** No one can write down how they read a position. The reading
  is specific to positions in worlds not yet authored — you can't pre-write it for a board you've
  never seen.
- **It has to land in a specific mind.** The estimator must compile into *this* agent's actual
  cognition, and you can't introspect your own estimator. So it's iterative no matter the model —
  you only find what reading actually fires by running it.

The payoff on top: the grown playbook is *portable*. A strong model may already read positions
fine, so growth looks marginal on it — but the playbook carries the reading to a weak model that
can't. That portable text is the one artifact you cannot hand-write, because it's the tacit
estimator made explicit. (Taste is the situational trigger, not the capability.) This last part is
a bet, not a proof — it's watched, never assumed (the port check).

## The goal is a portfolio, and its dynamics is the other half of taste

"Goal" in the functional was never one goal. It's a **portfolio**: a heavy main goal plus a small
**play** goal whose whole notion of worth is "is this teaching me something."

- **Transfer is a vector** — one component per active goal. How you collapse it to a number (norm,
  weighted sum, geometric mean) is the knob for *don't chase every anomaly*. Geometric mean is the
  interesting candidate: a position then needs *some* live thread to count, so pure noise dies while
  an interesting-but-orphan anomaly survives on the play component.
- **Stepping stones** are sidequests: high learning-progress, ~zero transfer to the main goal when
  you take them, pursued because they're interesting — and they *might* wire in later. They ride the
  play component, weight-limited so you don't wander forever.
- **Goal-spawning** is promotion: when a sidequest turns out to wire into the main goal, the agent
  mints a new subgoal that now carries real transfer weight.

The functional is a **snapshot** — what a position is worth *right now*, given the current
portfolio. The portfolio's motion over time — which goals form, how attention shifts, when a
sidequest is promoted, and (on the slowest clock) when the main goal itself is **revised or
dropped** — is the **other half**, and it's the part we *grow, never specify*. Taste is the snapshot
plus the dynamics.

This is also *why* the dynamics is grown rather than scored. The score's strong-play benchmark —
a credible mechanical ceiling on play under uncertainty, computed over the world family — can only be derived for a
**fixed** goal: it assumes the target doesn't move while you learn. So it scores the snapshot and is
structurally blind to the dynamics. There is no mechanical referee for how goals should form and
shift, so that half *cannot* be a target — only grown.

## What a world must be to demand taste

A world demands taste exactly when **reading Value(X) is the hard part**. It fails that in exactly
two ways — the two traps we keep walking into:

1. **Value is readable off the rules.** If you can write the best move down from the law without
   playing, it's calculation, not taste. (The threshold gate, stated cleanly: can Value(X) be
   computed from the rules? If yes, the world is below the line.)
2. **Transfer is a hop, not a path.** If the goal is one move away — nothing unlocks anything, no
   compounding — there are no stepping stones, only immediate payoffs, and a tasteless grab wins.
   (This was the trail. This was instance-0's flatness.)

So the world spec is one line: **make Value(X) un-guessable without playing, and put the goal many
linked moves away — each move unlocking the next (transfer is a path, not a hop)** — so a
position's worth is mostly *what it opens*, not what it pays on the spot.

## Who moves what — the integrity floor at every level

Nothing optimizes the functional; it's a lens, not a target. The three things that *do* move each
move against something else:

| What moves      | Optimizes against                                   | Genome                                   |
| --------------- | --------------------------------------------------- | ---------------------------------------- |
| the agent       | the score                                           | its playbook (text)                      |
| the smith       | the score-derived gates (hard · solvable · above-threshold) | the world's structure (a declarative spec) |
| the functional  | — (nothing)                                         | only humans sharpen it, via the wish channel |

The wall holds at each level: the agent can't touch the score; the smith proposes only *structure*,
and the referee and the strong-play benchmark (a credible mechanical ceiling, not necessarily the
exact optimum) are re-derived mechanically from it; the functional
is human territory, refined deliberately from what the loop surfaces, never self-modified. Letting
anything evolve its own definition of good is the wireheading line. *99% hands-off is the prize;
100% is wireheading.* And the artifact stays text — the playbook is read as context, never run.

## The one open thing this doesn't close

The portfolio dynamics — how goals form, how fast attention shifts, when a sidequest is promoted —
is named here and *deliberately left to grow*. We plant the world that makes good allocation win; we
never script the allocator. (The standing open question, carried from `DESIGN.md` §9.)

## What this supersedes, what it keeps

- **Supersedes** the *framing* of taste — the place we kept muddling. `DESIGN.md` §1 and the flat
  property-lists are replaced by the three layers and the functional above.
- **Keeps**, as the detailed second layer in `DESIGN.md`: the rules of the game (§2), "don't prove
  it, price it" (§3), the taste catalogue (§4), the world language and the smith (§5–§7), the
  standing decisions (§10), the wish channel.
- **History, not current:** everything under `history/`, and the toy-era worlds.
