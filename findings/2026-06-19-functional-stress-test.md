# Finding — stress-testing the value functional (2026-06-19)

A design session with the PI on `VISION.md`'s layer 2 — the functional
`Value(X) ≈ learning-progress · transfer / cost, biased to uncertainty`. Conclusions are now woven
into `VISION.md`; this note keeps the *reasoning* that got us there, so the edits aren't read as
arbitrary. Not a plan — a settled reading of what the functional is and isn't.

## What the functional absorbs (the part we kept misreading)

- **Forecasts all the way down — no "immediate" term.** You never *collect* value at a position; you
  predict what's learnable and predict what it opens, then spend a little to test the prediction.
  Sometimes the forecast is trivial, so you don't even spend that. The earlier "Bellman immediate
  reward" framing was wrong for exactly this reason: nothing is collected, everything is bet. Taste
  is just *the quality of those forecasts*.
- **`transfer` is the value function in disguise.** The depth — "a position's worth is mostly what it
  opens" — and the multi-horizon planning both live *inside* the transfer term, not as a separate
  recursion. So "downstream value" is not a missing factor; it's the whole content of transfer,
  weighted toward the goal portfolio. Stated plainly so nobody reads `transfer` as a
  closeness-to-goal scalar.
- **The learning term is itself a forecast**, and can be trivially 0 (already known) or trivially 1
  (free) — those don't trigger real probing.
- **Uncertainty-seeking is only weakly in the line.** The learning term leans toward the not-yet-
  known, but the sharp, non-myopic version (bet *across horizons* on what you're least sure of) is
  **grown, not written**. The crude rule of thumb does not give it for free — this was an overclaim
  we corrected.

## The A/B fork, resolved → B

Either (A) leave the value of a prospected position one fully-open estimate, no decomposition, all
grown; or (B) commit to the functional *form* as inductive bias and push the dynamics into the
transfer term. **We take B**, with the caveat stated out loud: once depth and goal-motion go into
transfer, transfer *is* the value function, not a relevance number. The form is the prior; the
content of transfer is grown.

## Snapshot vs. dynamics — the wall falls where the oracle can reach

- The **snapshot** (worth right now, given the current portfolio) is the part the functional seeds
  and the part the score can benchmark.
- The **dynamics** (which goals form, how attention shifts, sidequest promotion, and — slowest clock
  — revising or dropping the main goal) is grown, never specified.
- *Why* it's grown and not scored: the perfect-play benchmark assumes a **fixed** goal — best play
  under uncertainty only makes sense if the target doesn't move while you learn. So the oracle scores
  the snapshot and is structurally blind to the dynamics. There is no mechanical referee for
  goal-motion, so it can't be a target. The static-goal assumption is the seam.

## What the belief-MDP / oracle actually is (it is NOT an LLM)

Plain version: in a world you can't fully see, your "belief" is your current odds over the hidden
state given everything probed so far. The belief-MDP treats *that belief* as the thing you stand on
(you always know what you believe), turning "I can't see the truth" into "I can act on my own
uncertainty." Optimal play over beliefs values information for free — it'll take a move that pays
nothing but sharply narrows the possibilities, because that makes future moves better. That is the
shape of taste/probing. Crucially it is **best play knowing only what's been revealed**, not the
omniscient cheater.

Operationally, in the quarantined trail (`hta/_trail/anchor.py`): the oracle is exact, model-free,
token-free Python.

- `oracle_value` (`anchor.py:295`): value iteration over belief states. A belief is the set of
  worlds still consistent with what's probed; `V(H,b)` = "stop and submit" value vs. the best
  affordable probe, each probe's outcomes weighted by likelihood and recursed. That recursion *is*
  the belief-MDP optimum, planning to the budget horizon.
- `clairvoyant_value` (`anchor.py:320`): the omniscient ceiling (knows the true world) — context,
  not the gate. `belief-MDP ≤ clairvoyant`; the gap is the price of uncertainty.
- `floor_value` (`anchor.py:348`): the no-inference walker (probe cheapest cells, never infer).

Haiku is the **agent under test**, scored by coverage against the **floor→oracle band** — never the
oracle. "Oracle ≫ floor and ≫ best hand-writable heuristic" is the gate that the world demands taste.

## RL framing: the lab's ruler, not the agent's brain

The belief-MDP/RL view is computable only in the gym (small, deterministic worlds) and there it
gives ground truth — the score, the oracle, the calibration check. In the wild it is uncomputable,
and *that is the whole reason the project exists*: if the world were RL-solvable you'd run RL.
Taste is the cheap, portable heuristic that stands in for the value function you can never compute.
The apparatus is a bridge — ground truth in the lab → grown heuristic for the wild. The belief-MDP
never rides into the field.

## What we'd actually do to grow taste

Keep a functional, written the PI's way, but treat it as a **seed the playbook is meant to outgrow**
— do not pour effort into perfecting the formula (that's overfitting the lens, the layer explicitly
not meant to be the prize). The two places taste actually grows:

1. **The world-smith's diversity** — taste is domain-agnostic, so it can only be *defined* by worlds
   varied enough that no single tactic survives across them.
2. **The playbook's heuristic accumulation** — the portable text "in positions shaped like this, the
   downstream worth is usually there" — the tacit estimator made explicit.

## Two smaller settled points

- **Cross-world invariance is a thermometer, not fuel.** As a training objective it's too open to
  climb; as the *audit* that separates taste from tactic (alongside the port check) it's exactly
  right. Keep it on the wall, not in the loop.
- **Wish channel:** the only sacred rule is *the score never moves*. Everything else — worlds, lens,
  curriculum, "what would grow taste better overall" — is fair human territory, not only named taste
  failures.

## Edits landed

`VISION.md`: "The definition" now lists what the line absorbs (forecasts-only, transfer-as-value-
function, weak-uncertainty); layer 2 is named a *seed* meant to be outgrown, with leverage in world
+ playbook; the portfolio section adds goal revision on the slowest clock and the static-goal reason
the dynamics can't be scored.
