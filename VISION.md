# VISION — taste, derived from one starting point

> **Status: the north star.** What taste is, and why everything else in the repo has the shape it
> has. This rewrite starts from a single idea and *derives* the rest: the integrity floor, the demand
> a world must meet, the ledger of goals, what grows vs. what we fix. Each is shown to be **forced**
> by the start, not chosen. The cheapest test of all of it is `BET.md`; the detailed machinery is
> `DESIGN.md`; the prior intuition-era statement is `history/2026-06-23-vision-intuition-era.md`.
>
> **One reading rule:** everything is named by what it *does*, not by its slot in a scheme — there is
> no "layer 2". A term gets one plain sentence when first coined.

---

# Part I — The derivation

## 1. What taste is

Start where it actually earns its keep. In a **well-posed** problem you have an objective and a
gradient — a direction that visibly improves the score. There you don't need taste; you follow the
gradient, and taste would be strictly worse than computing the thing. Taste only pays in the other
case: the objective is **ill-defined**, there is no gradient, and yet you still have to move — you
must commit to a direction *before* the outcome of going there is knowable.

Ask what kind of guidance is even *type-compatible* with "I can't see the goal." Not a rule (you
can't state the criteria — that's what ill-defined means). Not a gradient (there isn't one). The
only thing left is a **learned map from the local features of where you are to an estimate of
whether moving this way leads somewhere good.** That object has a name in another setting: a value
function. But the reward that would normally train it is missing.

> **Taste is the value function of a search with no reward signal.** *(A value function scores a
> position by the future good it leads to; "no reward signal" means there's no external score to
> learn it from.)*

This is the natural instrument for open-ended search not by analogy but **by elimination** —
everything else needs a gradient you don't have. It is also why taste feels forward-looking and
slightly uncanny: it isn't grading the object in front of you, it's estimating **positional value**
— how much good-reachable stuff this position connects to, from local cues, before you've explored
forward. A fertile position is locally unremarkable but opens onto many further good ones; a dead
one is locally fine and leads nowhere.

## 2. The value it estimates — one scalar, and its few slopes

There is no quality-*label* to predict — by setup, no consensus yet on what's good. So what does the
read regress on? One scalar, and it's the same one under every quality judgment: **how short your
account of everything you've seen is, under your current model.** Two parts — the bits to write the
model down, plus the bits to encode the data once you have it. Low total is a good model, and is
exactly what *elegant* means: a small scheme that covers a lot. The total punishes both failure modes
at once — memorize everything and the model-bits explode (overfit, baroque); keep the model tiny but
explain nothing and the data-bits explode (trivial). The felt sense of quality is that sum held in
tension.

One correction, which the theory-of-everything case forces: it is **not** raw shortness. The shortest
possible account of the world is cheapest to *write* and astronomically expensive to *run forward*
into any usable consequence — the fundamental laws hand you no macroscopic behaviour you can reach. So
discount shortness by the cost of running it: the quantity taste tracks is the **cheap, effective
account at the scale you work** — depth, not brevity. (This is also what *interesting* is: not the
incompressible, which is noise, and not the shallow, which compresses to nothing, but the **logically
deep** — structure that was expensive to reach.)

Now the part that explains why the quality-signals are **few**, which we kept tripping over. Call the
scalar L. You can do only two things with a scalar: read its **level**, or read its **slope** along
some direction. So every quality-signal is L differentiated against a different variable — none is a
new substance; all are one object seen from a different angle. The count of distinct signals can't
exceed the count of distinct directions you can differentiate L in, and only a few mean anything:

- **Level — compression.** How much the position unifies what's already in view.
- **Slope vs. the object — rigidity.** Perturb it; does quality collapse. ("Couldn't easily be
  otherwise.")
- **Slope vs. your own time — learning progress.** Engage it; does your model get shorter. (The
  acquisition signal; its live form is the *rate* of compression progress.)
- **Slope vs. forward steps — generativity.** Step ahead; how many further good positions open.
- **Slope vs. your encoder — the right-abstraction move.** Does this change the vocabulary you
  represent things in, so your whole prior experience re-compresses cheaper. This one is special: it
  changes the apparatus that computes the other four, so it is the recursive term and sits apart.

That is why the list is short *and* why it can't also be orthogonal: a short list and an independent
list pull against each other, and here shortness wins because every entry descends from the one scalar
L — which is exactly what makes them non-independent. They are projections, not primitives. And every
one is **label-free**, because each is measured against your own model, not the world. That is the
whole content of "a search with no reward signal": **you supervise against yourself.** Hold onto that
— §5 turns on it.

## 3. What actually transfers across domains

The estimator itself does **not** transfer. A great wine palate has zero edge on chess; a value
function is a model of one geometry, domain-bound by construction. So whatever makes judgment feel
like it travels, it isn't the estimator. What travels is the **infrastructure that builds and runs
estimators**, and it is three organs that fire together — which is why they read back as one faculty:

- **The acquisition loop** — the skill of metabolizing a fresh domain into a working read fast. The
  experienced person didn't get better at music; they got better at *getting good at things*.
- **The invariant-sensors** — the part of "good" that survives deleting the domain. "Elegant" has a
  format-stripped signature (a compression win that pays off anywhere); once you can feel it in one
  place you can feel it everywhere, because you're detecting a property, not a subject.
- **Meta-calibration** — the read on your own read. Not "is this good" but "is my sense that this is
  good trustworthy *here*." Its object is your own signal, so it ports everywhere by default.

**This is the whole thesis.** The estimators you can always regrow per-domain once the infrastructure
is good — so the infrastructure is the only thing worth building directly. *Taste is the situational
trigger, not the capability:* the moves belong to the model; which one fires from the position-read is
the grown part, which is why it can port onto even a weak model.

## 4. Preference — the goal that gives the field a gradient

The value framing needs a direction to point at: with no goal, nothing is "good-reachable" and there
is no gradient to climb. So you supply one — an overarching goal, even a coarse one. This looks like a
special act ("positing the objective") but it is not a separate faculty: choosing the goal is **deep
downstream value-estimation** read one level up — *what does committing to this route open?* — and the
route is just another direction in the same value framing.

What the goal buys is organization. An overarching goal plus a small, stable **play** drive — whose
only notion of worth is "is this teaching me something" — keeps you from wandering and gets you to
actually *solve something*: everything orients, at least loosely, around the goal. That orientation is
the **transfer** idea — value weighted toward what carries to the goal. In the language of §2,
supplying the goal is what gives the otherwise-flat value field a "toward."

The goal is not frozen. It can change — slowly, or fast if the situation truly demands it (you made a
wrong bet). So even the top is revisable, on the slowest clock. But it is **the one thing we author**;
everything beneath it follows as value-estimation toward it. That single authored input is the whole
of what stays in human hands — the rest is grown (the 99/1 of §9).

---

# Part II — What the derivation forces

Now embed Part I in *our* setting: an agent we **select on**, playing **worlds we author**, to grow a
**portable artifact**. Each thing we learned the hard way falls out as a consequence — re-derived, not
imported.

## 5. The floor: the value-read *steers*, an external score *grades*

Section 2 says train against the slopes of your own model. Taken literally into an agent we optimize,
that is **wireheading**: the moment the agent's own signal becomes the selection pressure, the agent
is optimizing a thing it can move — sandbag the forecast, *look* like you're learning. That is the
trap that forced the reset, re-derived from first principles.

The escape is that the internal signal has **two jobs and they must not be the same job**:

- **Steering** — the value-read chooses the agent's next move *inside* an episode. This is supposed to
  be the agent's own, movable, growing read. Good.
- **Grading** — what selects one agent over another across episodes. This must be **external,
  mechanical, and untouchable by the agent**, or steering eats itself.

So a **dumb deterministic score the agent cannot reach** is forced — not as dogma, but as the only
guard that lets the self-supervision of §2 exist inside a selected agent without collapsing. The score
is **selection pressure, not the measure of success**: it cannot tell grown taste from a good-enough
imitation of perfect play. The measure of success is the **port lift** — does a weak model *plus the
grown artifact* beat the weak model *alone* on held-out worlds. The score selects; the port lift
judges. And the artifact stays **text, read as context, never run** — the same wall, since runnable
output can reach around the score.

## 6. The world must demand taste — and only where it's hard

A world demands taste exactly where **reading the value of a position is the hard part** — and the
sharp word is *where*, not *whether*. A grown agent should make ordinary competent progress on its own
and engage the slow, deliberate position-read only at the points where value genuinely can't be read
off — the switch into effortful "System 2" thinking, fired only when the fast read won't do. We don't
want taste forced on every move; we want it to fire where it pays. So a good world **hides its hard
points among tractable progress**, and *knowing when to switch* is itself the meta-calibration organ
of §3 — the read on whether your fast read is trustworthy here. A uniformly hard or uniformly easy
world teaches the wrong thing; one that demands the switch at the right moments grows the gate.

At those hard points a world still fails to demand taste in the two ways we keep walking into:

1. **Value is readable off the rules.** If the best move can be written down from the law without
   playing, it's calculation, not taste.
2. **The goal is one hop, not a path.** If nothing unlocks anything — no compounding — there are no
   stepping stones, only immediate payoffs, and a tasteless grab wins.

> **The world spec, one line:** make a position's value **un-guessable without playing**, put the goal
> **many linked moves away — each move unlocking the next**, and **bury the hard reads among easy
> progress** so the agent must learn *when* to spend taste, not just how.

## 7. Forecast the move — making the internal signal honest and measurable

"How can a model be surprised?" — literally, by **predict-then-reveal**: the agent commits a one-line
forecast *before* it probes (what it expects to learn, what that opens toward the goal, what it costs),
then acts, then treats the **gap between forecast and result** as the signal. Because our world is
deterministic and hidden, the world itself returns the true answer — so the surprise is measured
against reality, not against a judge that could be talked into anything.

That one move instruments the slopes of §2 that are cheap to read: **surprise** is the forecast error,
**learning progress** is that error trending down across the episode, **meta-calibration** is whether
the agent's stated confidence matches its hit rate. It is also the within-episode self-correction — a
model that never predicts can't be surprised, so nothing corrects it, which is the core failure mode
restated. Per §5 this forecast log is **instrumentation that steers**; it never becomes the graded
objective, or the agent games it.

## 8. The goal is a dynamic ledger, and a coverage-tilted score can grow it

"Goal" was never one goal (§4). It is a **dynamic ledger**: many goals at different weights and
timescales — a heavy, slow main goal; a light, fast play goal worth only "am I learning"; others that
form, get reweighted, get **promoted** when a side-thread turns out to wire into the main goal, and
dissolve. A **stepping stone** is a side-thread with high learning-progress and ~zero transfer to the
main goal when you take it, ridden on the play weight, kept because it might wire in later. The
value-read is the **snapshot** — what a position is worth right now given the ledger; the ledger's
**motion** is the other half of taste, and it's grown, never scripted.

We don't script the allocator. The question is whether it can be *selected for*, since a perfect-play
benchmark wants a **fixed** goal and the ledger's whole point is that the goal moves. The way through —
and it looks right — is to **tilt the external score toward how much you covered**, not toward reaching
one target cheapest. Then "perfect play" stops being "hit the single goal for least cost" and becomes
**"covers a lot."** A one-track greedy agent now scores *lower* on the final exam even when it reached
its one goal cheaply, because it skipped the stepping stones — including ones that would have spawned a
richer subgoal worth following instead. The coverage tilt makes a good allocator win on the score
directly, so the dynamics becomes selectable **without anyone scripting it**. Stochasticity is fine:
under a moving goal there is no single perfect policy, only "covers more." And it is grown across
**many** worlds, not one — the agent learns that play pays across varied situations, which is where the
growth gets interesting.

This stays inside the floor (§5): "how much you covered" is a **mechanical** coverage measure — the
information the agent has pinned down — read externally, never the agent's self-report of how much it
learned. So the open part is no longer *whether* the allocator can be grown but *how well* this
coverage-tilted, multi-world setup actually grows it.

The tilt itself shouldn't be a constant. How far breadth outweighs depth depends on the situation and
on how stable we've declared the top preference to be (§4) — which is a setting we supply, plausibly a
**user config** rather than a fixed law. At the unstable end, one concrete mechanism is to let the
agent *surface* the choice — "this thread looks worth more than the main goal; promote it?" — and have
a human answer, i.e. §4's slow top-revision made interactive. The catch is honest: every promotion a
human decides is one the allocator didn't grow, so this escalation channel buys control at the cost of
growth, and where to draw the line — which promotions the agent commits to vs. escalates — is itself
open.

## 9. Nothing evolves its own definition of good

Three things move, and each moves only against something it cannot itself touch:

- **The agent** revises its own read — text it writes — against the **external score** (§5). It can't
  reach the score.
- **The world-author** proposes only the world's **structure**, against gates re-derived mechanically
  from that structure: still **hard** (good play beats greedy) and still **solvable** in budget. It
  never touches the score — an author that could move the score would just mint worlds that *look*
  solved.
- **The seed-read** (the crude starting estimator) is optimized by **nothing**; only humans revise it,
  deliberately, from what the loop surfaces.

The single rule under all three: **nothing evolves its own definition of good** — that is the
wireheading line, and the only thing held out of the loop by hand is the top preference of §4. *99%
hands-off is the prize; 100% is wireheading.*

---

## Appendix — the prior functional, carried as desiderata only

The earlier north star ran on a hand-written functional — `Value ≈ learning-progress · transfer /
cost, biased toward what you're least sure of`. It was **intuition, not derived**, and it is *not*
load-bearing here. A later session should **rederive** something like it from the field of §2 rather
than patch it. It is carried along only as the desiderata it was groping for: value is **forecasts all
the way down** (no "immediate" term — you predict, then spend a little to test, §7); **transfer is the
downstream worth of what a move opens**, not a closeness-to-goal number; and **"biased to uncertainty"
is an estimator trick, not part of what value is** — the tell that the whole line is estimator-level,
hence improvable. The full prior statement is in `history/2026-06-23-vision-intuition-era.md`.
