# PASS3_REDO — the converging picture (working capture, 2026-06-13)

> **Status: the definition is settled; the rest is stable but not locked.** Live answer to
> `NEXT.md`'s question (what a world is, and the rule for making worlds). The taste definition
> (§1) is settled. The rules-of-the-game list (§2) is validated but provisional — a starting
> point a later session may sharpen. The machinery (§3–§7) is stable. **Not yet locked:** on
> explicit PI sign-off this folds into `PLAN.md`'s record v2 §1, a cold-reader subagent reads
> the rewrite, and only then do the draft banners come off the other docs.

---

## 1 — The definition (settled this session)

> **Taste is choosing your next move well by evaluating your position.**

That's the whole thing. (The "situational trigger, not the capability" line is the *thesis* —
why it's worth growing and why it should port to a weak model — not part of the definition.)

## 2 — The rules of the game (what any world must have) — validated, still a starting point

The conditions a world must meet to measure taste. We checked them the honest way: three fresh
instances, given only the definition and nothing about this project, each wrote down almost the
same list without talking to each other. That independent agreement is our evidence the list is
real and not back-fitted to what we already believed. It is a **starting point, not final** — a
later session may sharpen it.

- more than one move to pick from;
- which move is good **depends on where you are** (or one memorised answer wins);
- a **dumb outside scorer** the player can't influence (never an LLM judge);
- a **fresh case every episode**, so the player must carry a method over, not memorise a case;
- **no cheap formula** that hands you the best move — if there is one, it's calculating, not
  taste (this is the old "threshold gate");
- **enough is findable that skill beats luck** across the world — but **not everywhere**. Some
  regions are dead ends or noise where the answer can't be found, and the right move is to
  notice and turn around. Spotting that is itself taste — the boredom / learning-gradient
  habit, salted in on purpose;
- **many rounds averaged**, so luck washes out;
- a **real gap between sharp play and lazy play**, and that gap opens only by changing the
  world's **shape, not its size**.

What the cold reads said was *not* required — hidden state, a probe budget, a long horizon, an
oracle to grade against — we treat as our **choices**, not rules (see §5).

## 3 — "Don't prove it, price it" (the method that makes the open parts safe)

The actual method of the whole project, and the thing that lets us live with what we can't yet
prove:

> **Never certify the good outcome up front. Arrange things so the bad outcome is visible and
> costs points, and keep the lever to fix it in our own hands.**

It answers the standing worries with one move:

- **Expressibility** — we can't prove the world language can say every world taste needs. We
  don't have to. If it can't express the world that teaches some habit, the smith simply can't
  ship that world, and that catalogue entry sits unrealised — *visibly*. The lever: new parts
  come through us, deliberately.
- **Forgetting across stages** — held-out draws and the standing baseline still include the
  earlier worlds, so a playbook that forgot an early habit loses points and gets rejected.
- **Transfer to real taste** — watched, not assumed: the port check (the playbook on a
  different model), an outside task family the smith never touched, a watch for leaked
  world-internals vocabulary. All read-only to selection, or they rot into targets.

## 4 — The taste catalogue, read two ways

> **One list, read from two sides. As behaviour, it's the taste habits we want. As
> engineering, it's the demands on what the world language must be able to say** — each habit
> names a world the language has to be able to build. So the catalogue also tells us *when* to
> grow the language (an entry with no world that teaches it).

- The **taste catalogue** = our private wishlist of tasteful habits. Each is one habit we want
  — not a "row", just one item in the set.
- A **habit** = one of those once selection has written it into the playbook.
- **Plant the condition, never the response.** We build the world that makes a habit the
  winning move (the dead-end vein); we never write "leave when bored" anywhere. We never reward
  taste or hand it a target — we shape what it's up against, and the good behaviour shows up.
- **Rediscovery test** = build the world, then read the evolved playbook for the habit *in its
  own words*, with no one having written that sentence for it. We keep the catalogue private
  and check it ourselves; show it to any agent the player sees and we'd be measuring copying.
- **Learning gradient** (the give-back dial, formerly mis-named "lawfulness") = how much a
  region pays back when you study it, steep where each probe teaches a lot, flat in noise.
  Following it, and quitting when it goes flat, is the habit; the dial is the world feature
  that makes that habit pay.
- **Diet + leak wall** — the catalogue is in the **smith's** reading list only. Safe there
  because everything the player sees is re-expressed through a flat interface first (region 7,
  variable 3 — never the smith's labels), so the smith's words never reach the player.

## 5 — The world language, and our world as one instance

What we hand the smith is neither a finished world nor bare principles — it's a **language for
describing worlds**: a small box of part types plus the rules for wiring them. The smith writes
a description in that language; the lab checks it's well-formed, builds the world, and computes
the answer key — all mechanically, because the parts are ours. The smith's freedom is
everything the parts combine into (huge); the safety is everything the language **cannot say**
(it cannot describe a world we can't grade). A chess-problem composer: endless fresh problems,
real creativity, inside rules it can never touch.

This is the in-between the earlier sessions kept missing — we kept writing the *world* when the
thing to settle was the *grammar*. A finished world is too tight (it rereads and extends one
spec forever); bare principles are too loose (it games the gates or writes nonsense). The
language is the missing middle. Each world it writes is **one instance**, disposable.

**The cold reads settled the thing we kept tripping on.** Hidden structure found by costly
probing — our whole world — is **one way** to meet the rules in §2, not the only way and not
required. A fully-visible game (chess-like) meets the same rules. So our world is **one valid
instance**, and the smith could build other kinds. Naming it as one instance is the cure for
what kept locking us in: we'd been treating a choice as a law.

- New part types are code, so they arrive **through us** — deliberately, surfaced by the wish
  channel and the exhaustion signal when the box is the bottleneck.
- **Smith diet:** each call it reads the rules of the game, the parts box, the catalogue, and
  where the champion is losing points — never the previous world's full wiring. Anchoring comes
  from what's in front of it, so don't put the old world in front of it.

## 6 — Staging stages itself

You can't have one world that exercises all of taste, any more than one exam question tests all
of mathematics — and you don't need to, because it's one skill that shows up in many
situations, so growing "scout before you commit" and later "drop a dead vein" thickens the same
muscle. The carried playbook is how exposure adds up instead of resetting.

And it's self-enforcing: a world that piles on three new demands at once is too hard, the
champion can't be coached to it, so it fails the ship-gate and bounces. "One new thing at a
time" is what **coachability** already buys — not a guardrail we install.

*(Later chapter, written down: the smith choosing which world to pose next is itself taste, one
level up. For now the ship-gate hard-wires the champion's edge; growing the smith's own taste
is a later chapter, not now.)*

## 7 — The smith: authoring and search don't cleanly split

A useful mental model is two pieces — **authoring** (write a world as a parts-list) and
**search** (propose many, gate them, keep the one at the champion's edge). But they don't
separate cleanly: the gap a world needs (sharp play far above lazy play) is a property of the
world's **shape, not its size**, so you can't turn it on with a knob — you have to change
structure. Hand-building one good world is therefore already hunting over shapes, which is
search.

What *is* deferrable: the **automated search across many candidates** — there's nothing to
select among until there's variation. And the **first champion is just the bare student** (day
zero has no other), so the ZPD check runs from the start against it. Agreed regardless: build
the language/builder/gates first (needed on every path), and author instance 0 as a real
parts-list in the language so it's the smith's worked example, not a throwaway.

## 8 — Naming

**In use:** the **definition** (§1, settled) · the **rules of the game** (§2, what a world must
have) · **"Don't prove it, price it"** (§3) · the **taste catalogue** (habits, not "rows") · the
**world language** (instances are disposable) · the **learning gradient** (the give-back dial).

**Retired — don't reuse:** curvature, faces, lawfulness, world properties, clauses, spine. And
the "what capability doesn't buy" clause is retired **from the definition only** — it lives on
as the *thesis* (taste is the situational trigger, not the capability) and the measurement angle
(the port check), never as what taste *is*. See §1.

## 9 — Open

1. **The rules-of-the-game list (§2)** is validated but provisional — possibly its own short
   session to sharpen.
2. **How much of the world language to build first** for the proof of principle (the kit's
   first slice), and the implementation details record v2 §2–§7 still owe (part formats, the
   exam-drawing, the probe interface, calibration constants).

## 10 — Process / next move

Not locked. Existing draft banners stay on (`PLAN.md` record v2, `ROADMAP.md`). On PI sign-off
this folds into record v2 §1 as definition-plus-rules-plus-one-instance, a cold-reader subagent
reads the rewrite, and the banners come off. Then the implementation milestone (the world
language's first slice + instance 0 + the inner-loop proof of principle) as record v2 describes.
