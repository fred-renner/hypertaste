# PASS3_REDO — the converging picture (working capture, 2026-06-13)

> **Status: working capture, NOT locked.** This is the live answer to `NEXT.md`'s single
> question (the world abstraction + the generative principle for worlds), written down so a
> long brainstorm isn't lost to context. The machinery picture below is settled enough to
> carry forward. **Two things are still open and must not be treated as decided:** the exact
> wording of the taste axiom (§1), and whether the smith's *authoring* and *search* separate
> cleanly enough to defer the search (§7). When the axiom locks, this folds into `PLAN.md`'s
> "Pass-3 design record v2 §1" as principle-plus-instance, a cold-reader subagent reads it,
> and only then — on explicit PI sign-off — do the draft banners come off.

---

## 1 — The axiom (the definition everything derives from) — WORDING OPEN

Don't list properties of the world and hope they're complete. Start from one sentence that
says what taste *is*, and let the rest of the design fall out of it. This sits above the
machinery as its own line — it's axiomatic, the highest thing in the hierarchy, not a spine
through the middle.

**The working sentence (PI's, the one with the right energy):**

> *Taste is choosing your next move well from evaluating your current position under varying
> downstream knowledge and resource constraints.*

Where the magic lives: **"well."** Choosing well means reading the position — what you know,
what a move would cost, what it would open downstream — and picking the high-leverage move,
rather than working down a checklist. "Varying downstream knowledge" is the honest version of
the leverage/reach idea: how much you know about where a move leads *differs* across moves,
and gathering more is itself one of the moves you're choosing between.

**The structural fix that stops it feeling hedged (the level confusion):** "never from a
fixed rule" does **not** belong in the definition. The *agent* absolutely forms rules —
heuristics, rules of thumb — and a grown playbook *is* a set of them; that's how taste is
carried. What must have no closed-form rule is the **world**: its optimal play must stay
tacit, or a solver trivialises it and the loop is theatre. So "no napkin solver" is a
property the *world* must have to **measure** taste — it lives in the rules of the game (§2),
not in what taste is. Pulling it out of the definition is what dissolves the "but the agent
needs heuristics, and "never" is too strict" objection, and it lets the agent work the easy
cases too.

**Still open:** the exact words. The sentence should be a nudge abstract (definitional), must
not over-constrain ("once", "never", strict "goal > budget" all flagged too strict), and must
survive being read from first principles rather than reverse-engineered to fit a list. Whether
the resource/constraint tail needs naming at all ("next move" already implies scarcity) or
must be explicit to be *buildable* is part of what's open.

## 2 — The rules of the game (the measurement conditions, derived from the axiom)

Not "world properties" — these are constitutive for the **whole project**, the conditions a
world family must meet for what we measure to actually be taste. Each one kills a specific way
the measurement could be a sham, and they **derive from the axiom** rather than being
hand-picked — which is also why they're complete *relative to the sentence* and would change
if the sentence does. They are not eternal.

- moves **cost**, and spending here forecloses spending there → scarcity;
- there is a **position to read** — hidden structure you hold partial, uneven knowledge of;
- the optimal play has **no closed-form rule** (the threshold gate / solver-proofness — now
  seen as the world-side restatement of the axiom, not a separate bolted-on gate);
- there is **more worth doing than you can do** → real allocation, not a free computation;
- truth is **planted by us** (checkable by arithmetic, never a judge) and **partly
  patterned** (a few probes predict many answers — else there's nothing to be tasteful about),
  graded only on **predicting behaviour never observed**.

Name: **the rules of the game.**

## 3 — The no-certificate rule (the recurring move — keep its spirit)

The actual method of the whole project, and the thing that makes every open worry tolerable
instead of blocking:

> **We never certify the good outcome up front. We arrange things so the bad outcome is
> visible and costs points, and we keep the lever to fix it in our own hands.**

It's the integrity floor, generalised, and it answers most of the standing worries with one
move:

- **Expressibility** — we can't prove the world language can express every demand taste
  makes. We don't have to. If it can't express the constraint that makes some habit pay, the
  smith simply can't ship a world that teaches it, and that catalogue entry sits unrealised —
  *visibly*. The lever is named: new component types come through us, deliberately. So
  expressibility isn't a claim we defend; it's a frontier the catalogue maps and we extend on
  demand.
- **Forgetting across stages** — held-out draws and the standing baseline still include the
  earlier worlds, so a playbook that forgot an early habit loses points and selection rejects
  it. Forgetting is penalised, not wished away.
- **Transfer to real taste** — monitored, not assumed: the port check (champion playbook onto
  a different student), an alien task family the smith never touched, the vocabulary watch.
  All read-only to selection, or Goodhart eats them.

## 4 — The taste catalogue, read two ways

The framing that made the catalogue stop being a hand-list:

> **The catalogue is one list read from two sides. Read as behaviour, it's the taste habits we
> want. Read as engineering, it's the requirements on how expressive the world language must
> be** — because each habit names a constraint the language has to be able to express. So the
> catalogue also tells us *when* to grow the language (an entry with no home) and roughly
> *what* to add.

- The **taste catalogue** = our private wishlist of tasteful behaviours (= the "virtues"). Each
  is just a habit we want — not a "row", just one thing in the set.
- A **habit** = one of those once selection has actually written it into the playbook.
- **Plant the condition, never the response.** We build the world feature that makes a habit
  the winning move (the dried-up vein); we never write "leave when bored" anywhere. This is the
  Friston/constraints reframe: we never reward taste or hand it a target — we shape what it's
  up against, and the good behaviour precipitates. The catalogue is a list of *constraints*,
  not *targets*.
- The **rediscovery test**: build the feature, then read the evolved playbook for the habit in
  its *own words*, with no one having written that sentence for it. We keep the catalogue
  private and score against it ourselves — show it to any agent the player can see and we'd be
  measuring copying.
- **Learning gradient** (the dial formerly mis-called "lawfulness"): how much a region gives
  back when you study it — steep where each probe teaches a lot, flat in pure noise. Following
  it (and knowing when it's gone flat and to walk away) is the taste; the dial is the
  world-side feature that makes that habit pay.
- **Diet + leak wall:** the catalogue is in the **smith's** reading list only. It's safe there
  because everything the player sees is re-expressed through the generic interface first
  (region 7, variable 3 — never the smith's labels), so the smith's words never survive the
  trip to the player. The guard is "the smith's names don't reach the player," not policing the
  smith's vocabulary.

## 5 — The world language and its first instance

> **Here is what any world must do (§2), here is the first language for saying one, and here is
> why we're not afraid the language is incomplete (§3).**

The thing we hand the smith is neither a finished world nor bare principles — it's a
**language for describing worlds**: a small box of component types plus the rules for wiring
them. The smith writes a description in that language; the lab checks it's well-formed, builds
the world, and computes the answer key — all mechanically, because the parts are ours. The
smith's freedom is everything the parts combine into (huge); the safety is everything the
language *cannot say* (it cannot describe a world we can't grade). A chess-problem composer:
endless fresh problems, real creativity, inside rules it can never touch.

This is the in-between the previous sessions kept missing — we kept writing the *sentence*
when the thing to settle was the *grammar*. A finished world is the too-tight end (it rereads
and extends one spec forever); bare principles are the too-loose end (it games the gates or
writes nonsense). The language is the missing middle. Instance #1 is **disposable** — one
sentence in the grammar, not "the world".

- New component types are code, so they arrive **through us** — deliberately, rarely, surfaced
  by the wish channel and the exhaustion signal when the box is the bottleneck.
- **Smith diet:** each call it reads the rules of the game, the parts box, the catalogue, and
  where the champion is currently losing points — never the previous world's full wiring as a
  starting point. Anchoring comes from what's in front of it, so don't put the old spec in
  front of it.

## 6 — Staging stages itself

You can't have one world that exercises all of taste, any more than one exam question tests
all of mathematics — and you don't need to, because it's one skill that shows up in many
situations, so growing "scout before you commit" and later "abandon a dead vein" thickens the
same muscle. The carried playbook is the integration mechanism: exposure accumulates instead
of resetting (LLMs train in stages; humans learn by integration — same shape).

And it's self-enforcing: a world that piles on three new demands at once is too hard, the
champion can't be coached to it, so it fails the ship-gate and bounces. "One new thing at a
time" is what **coachability** already buys — not a guardrail we install.

*(Later chapter, write it down: the smith choosing which world to pose next is itself taste,
one level up — learning-progress curricula. For now the ship-gate hard-wires the champion's
edge; growing the smith's own taste is a later chapter, not now.)*

## 7 — The smith: authoring vs search, and sequencing — OPEN

A useful mental model: the smith has two pieces. **Authoring** — read the rules of the game,
the language, the catalogue, and write a world as a parts-list. **Search** — propose many
candidates, run each against the gates, keep the one at the *evolved champion's* edge.

The clean-sequencing claim ("build the language, author instance 0 by hand inside it, turn on
the search only once there's a champion") is **not settled** — the PI's open doubts, kept
honestly:

- Do authoring and search **decouple cleanly**? Probably not fully. Authoring a parts-list
  that can express a catalogue point already requires reasoning about how deep the assembly
  must go — that's proto-search. They bleed into each other.
- **Why not make the bare student the first champion?** On day zero the only student is the
  bare one — so the ZPD gate can run against it from move zero, and instance 0's "champion" =
  the bare/day-one student (which is the proof-of-principle's own measurement anyway). The
  thing genuinely deferrable is then only the **multi-candidate search automation**, not the
  champion concept.
- So the live question is narrower than "hand-build vs smith": it's *how much of the smith's
  machinery must stand up at instance 0*, given that authoring-in-the-language is the
  knowledge the smith needs anyway and shouldn't be thrown away as a one-off.

What **is** agreed in this area: build the language/builder/gates regardless (needed on every
path); author instance 0 as a real parts-list in the language (not a throwaway — it becomes
the smith's worked example); don't put the old spec in the smith's face.

## 8 — Naming ledger

**Adopted:** the **axiom** (the one-sentence definition, wording open) · the **rules of the
game** (the measurement conditions) · the **no-certificate rule** (the recurring move) · the
**taste catalogue** (wishlist of habits; entries are habits, not "rows") · a **habit**
(internalised, in the playbook) · the **world language** (the smith's vocabulary; instances
are disposable) · **learning gradient** (the give-back dial).

**Retired — do not reuse:** curvature, faces, lawfulness, world properties, clauses, spine.

## 9 — Open questions (carry into the next exchange)

1. **The axiom's exact words** (§1) — first-principles, definitional, no over-strict
   conditions, "no fixed rule" kept out of the definition and parked in the rules of the game.
2. **The smith at instance 0** (§7) — do authoring and search separate enough to defer the
   search; is the bare student the first champion; how much machinery stands up first.

## 10 — Process

Not locked. Existing draft banners stay on (`PLAN.md` record v2, `ROADMAP.md`). This file is
the working capture; on the axiom lock it folds into record v2 §1 as principle-plus-instance,
a cold-reader subagent reads the rewrite, and the banners come off only on explicit PI
sign-off. Then the implementation milestone (kit v1 + instance 0 + the inner-loop proof of
principle) exactly as record v2 describes.
