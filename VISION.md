# VISION — taste, derived from one starting point

> **Status: the north star.** What taste is, and why everything else in the repo has the shape it
> has. This rewrite (2026-06-23) starts from a single idea and *derives* the rest: the integrity
> floor, the demand a world must meet, the portfolio of goals, what grows vs. what we fix. Each is
> shown to be **forced** by the start, not chosen. The intuition-era statement these conclusions came
> from is kept at `history/2026-06-23-vision-intuition-era.md`. The cheapest test of all of it is
> `BET.md`; the detailed machinery is `DESIGN.md`.
>
> **Reading rule for this doc (and the cure for the old one):** everything is named by what it *does*,
> never by its position in a scheme. There is no "layer 2." A statement about *function* survives the
> inside/outside line moving as models get stronger; a statement about *which box does it* rots. When
> a term is coined, it gets one plain sentence on first use.

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

## 2. How you train a value function with no labels

There's no external reward to regress on — by setup, no consensus yet on what's good. So you
supervise against the only thing available: **derivatives of your own model.** A handful of signals
carry it, and all are label-free because each is measured against *you*, not the world:

- **Learning progress** — does occupying this position make your model of the domain better. Not "is
  the object good" but "does engaging it improve my map."
- **Surprise that resolves** — a prediction that broke *and then folded into a simpler account*. Pure
  surprise is noise; pure confirmation is boredom; the signal is the violation that compresses.
- **Generativity** — how many further good positions the move opens. Forward-looking, recursive.

The single scalar underneath all of them is how short your account of experience is — a small scheme
that covers a lot. With one correction your own reasoning forces: it is **not** raw shortness. The
shortest possible account (a theory of everything) is cheapest to write and astronomically expensive
to *run forward* into anything you can use, and gives you no macroscopic behaviour. So the quantity
taste tracks is shortness **discounted by the cost of running it** — the cheap, effective account at
the scale you operate, not the ultimate one. Depth, not brevity.

## 3. What actually transfers across domains

The estimator itself does **not** transfer. A great wine palate has zero edge on chess; a value
function is a model of one geometry, domain-bound by construction. So whatever makes judgment feel
like it travels, it isn't the estimator. What travels is the **infrastructure that builds and runs
estimators**, and it is three organs that fire together — which is why they read back as one
faculty:

- **The acquisition loop** — the skill of metabolizing a fresh domain into a working read fast. The
  experienced person didn't get better at music; they got better at *getting good at things*.
- **The invariant-sensors** — the part of "good" that survives deleting the domain. "Elegant" has a
  format-stripped signature (a compression win that pays off anywhere); once you can feel it in one
  place you can feel it everywhere, because you're detecting a property, not a subject.
- **Meta-calibration** — the read on your own read. Not "is this good" but "is my sense that this is
  good trustworthy *here*." Its object is your own signal, so it ports everywhere by default.

**This is the whole thesis.** The estimators you can always regrow per-domain once the infrastructure
is good — so the infrastructure is the only thing worth building directly. *Taste is the situational
trigger, not the capability:* the moves belong to the model; which one fires from the position-read
is the grown part, which is why it can port onto even a weak model.

## 4. The one irreducible point — authorship of the apex

The deepest-looking taste-acts — *this problem is worth the field's attention, this is the right
abstraction* — look like they escape the value-function story, because they **posit** an objective
rather than estimate toward one. But positing is itself a position-read one level up: it decomposes
into recognizing that the current position affords a high-generativity declaration, and sensing that
*now* is the moment it will take. Both are reads. So it collapses back into value-estimation — with
exactly one exception.

The exception is the **apex**: the goal with nothing above it. There the read has no referent (there
is no higher quantity to estimate generativity *toward*), and it is self-fulfilling (pursuing it makes
the field reorganize around it, so the verdict is part of what makes itself true). That is authorship,
not estimation, and it does not reduce. But it shrinks to a **single point**. Below the apex, given
*any* fixed goal, spawning and ranking sub-goals is ordinary value-estimation toward that fixed top —
fully growable by the signals above.

> **The design consequence:** supply the apex by hand; grow everything beneath it. The irreducible
> authored part is one sentence you write, not a faculty you have to evolve.

---

# Part II — What the derivation forces

Now embed Part I in *our* setting: an agent we **select on**, playing **worlds we author**, to grow a
**portable artifact**. Each thing we learned the hard way falls out as a consequence — re-derived, not
imported.

## 5. The floor: the value-read *steers*, an external score *grades*

Section 2 says train against derivatives of your own model. Taken literally into an agent we optimize,
that is **wireheading**: the moment the agent's own signal becomes the selection pressure, the agent is
optimizing a thing it can move — sandbag the forecast, *look* like you're learning. That is the trap
that forced the reset, re-derived from first principles.

The escape is that the internal signal has **two jobs and they must not be the same job**:

- **Steering** — the value-read chooses the agent's next move *inside* an episode. This is supposed to
  be the agent's own, movable, growing read. Good.
- **Grading** — what selects one agent over another across episodes. This must be **external,
  mechanical, and untouchable by the agent**, or step 5 eats itself.

So a **dumb deterministic score the agent cannot reach** is forced — not as dogma, but as the only
guard that lets the self-supervision of Part I exist inside a selected agent without collapsing. The
score is **selection pressure, not the measure of success**: it cannot tell grown taste from a
good-enough imitation of perfect play. The measure of success is the **port lift** — does a weak model
*plus the grown artifact* beat the weak model *alone* on held-out worlds. The score selects; the port
lift judges. And the artifact stays **text, read as context, never run** — the same wall, since
runnable output is output that can reach around the score.

## 6. The world must demand taste

Section 1 says taste pays only where the objective is ill-defined and the value isn't computable in
advance. Turn that into a spec for a world worth playing. A world demands taste exactly when **reading
the value of a position is the hard part**, and it fails that in the two ways we keep walking into:

1. **Value is readable off the rules.** If the best move can be written down from the law without
   playing, it's calculation, not taste.
2. **The goal is one hop, not a path.** If nothing unlocks anything — no compounding — there are no
   stepping stones, only immediate payoffs, and a tasteless grab wins.

> **The world spec, one line:** make a position's value **un-guessable without playing**, and put the
> goal **many linked moves away — each move unlocking the next** — so a position is worth mostly *what
> it opens*, not what it pays on the spot.

## 7. Forecast the move — making the internal signal honest and measurable

"How can a model be surprised?" — literally, by **predict-then-reveal**: the agent commits a one-line
forecast *before* it probes (what it expects to learn, what that opens toward the goal, what it costs),
then acts, then treats the **gap between forecast and result** as the signal. Because our world is
deterministic and hidden, the world itself returns the true answer — so the surprise is measured
against reality, not against a judge that could be talked into anything.

That one move yields all three label-free signals at once: **surprise** is the forecast error,
**learning progress** is that error trending down across the episode, **meta-calibration** is whether
the agent's stated confidence matches its hit rate. It is also the within-episode self-correction — a
model that never predicts can't be surprised, so nothing corrects it, which is the core failure mode
restated. Per §5 this forecast log is **instrumentation that steers**; it never becomes the graded
objective, or the agent games it.

## 8. The goal is a portfolio, and its motion is grown, not graded

Section 4 said: supply the apex, grow everything below. "Everything below" has structure, and it is the
other half of taste. The "goal" was never one goal — it's a **portfolio**: a heavy main goal plus a
small **play** goal whose only notion of worth is "is this teaching me something."

- **Transfer is a vector**, one component per live goal; how you collapse it to a number is the knob
  for *don't chase every anomaly*. (Geometric mean is the interesting candidate: a position then needs
  *some* live thread to count, so pure noise dies while an interesting orphan survives on play.)
- **Stepping stones** are sidequests — high learning-progress, ~zero transfer to the main goal when
  taken, ridden on the play component, weight-limited so you don't wander forever.
- **Promotion** is when a stepping stone turns out to wire into the main goal and the agent mints a
  subgoal that now carries real transfer weight.

The value-read is the **snapshot** — what a position is worth right now, given the portfolio. The
portfolio's **motion** — which goals form, how attention shifts, when a sidequest is promoted, and on
the slowest clock when the main goal is revised — is grown, never specified. And it *has* to be:
re-deriving a credible perfect-play benchmark (§5's grader) needs a **fixed** goal, so the grader can
score the snapshot but is structurally blind to the motion. No mechanical referee for how goals should
form means that half **cannot** be a target — only grown. **This is the one genuinely open thing.** We
plant the world so good allocation wins; we never script the allocator.

## 9. What moves what — the wall at every level

| What moves           | Optimizes against                                  | Genome (what's evolvable)              |
| -------------------- | -------------------------------------------------- | -------------------------------------- |
| the agent            | the external score                                 | its playbook / read, as text           |
| the world-author     | the score-derived gates (hard · solvable · above the line) | the world's *structure*, a declarative spec |
| the value-read itself| nothing — it's a lens, not a target                | only humans sharpen it, deliberately   |

The wall holds at each level. The agent can't touch the score. The world-author proposes only
**structure**; the referee and the perfect-play ceiling are re-derived mechanically from it, and a
world ships only if still **hard** (perfect play ≫ greedy) **and solvable** within budget — an author
that could also move the score would just mint worlds that *look* solved. The value-read is human
territory, refined from what the loop surfaces, never self-modified. Letting anything evolve its own
definition of good is the wireheading line: **99% hands-off is the prize; 100% is wireheading** — and
the 1% we keep is exactly §4's apex authorship, supplied on purpose.

---

# Appendix — the crude seed-estimator, demoted to what it is

We do hand the agent a starting read, to get it off the ground:

`Value(X) ≈ learning-progress(X) · transfer(X → goal) / cost`, biased toward what you're least sure of.

This is **not truth and not a target** — it's the crude, hand-written seed the grown read is *meant to
outgrow*, and nothing optimizes against it. We don't pour effort into perfecting it; polishing the part
that's meant to be crude is just overfitting the lens. The leverage is in the world (§6) and the grown
text (§3), not the formula. Three things it absorbs so it isn't misread: it is **forecasts all the way
down** (no "immediate" term — you predict, then spend a little to test, per §7); **transfer is the
value function in disguise**, the multi-horizon worth of what a move opens, not a closeness-to-goal
number; and **"biased to uncertainty" is an estimator trick, not part of what value is** — which is the
tell that the whole line is estimator-level, hence improvable.

A note on why the quality-signals are *few* (§2), since it recurs: there is one scalar — the
description length of your model — and you can only read its **level** (how well it compresses now) or
its **slope** along the few directions that exist: against the object (rigidity — does value survive a
perturbation), against your own time (learning progress), against forward steps (generativity), and
against your encoder (the right-abstraction move — does this change the vocabulary you read positions
in). Few directions, so few signals. Treat them as **reading vocabulary** for building worlds and
naming what the loop discovers — **never as runtime scorers**, since the only thing that scores at
runtime is the one dumb external number of §5.
