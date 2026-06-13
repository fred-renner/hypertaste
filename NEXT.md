# NEXT — the entry point (written 2026-06-12, closing the Pass-3 redo sessions)

> **Update 2026-06-13 — the single question below is settled.** The Pass-3 redo brainstorm ran.
> Outcome in `PASS3_REDO.md`: the taste definition ("choosing your next move well by evaluating
> your position"), the rules of the game (what any world must have — validated by independent
> cold reads, still provisional), and our hidden-probe world as **one instance**, not the world.
> Next is no longer a brainstorm: **build instance 0** — the proof of principle (the world
> language's first slice + one hand-authored world + the inner-loop test). The question below is
> kept as the record of what was asked.

**For the next session: a PI design brainstorm. One question. Design only, no
implementation, $0. Brainstorm together — never lock solo; explicit PI sign-off before any
doc changes status; plain language per the CLAUDE.md rule.**

## Where things stand

- **Machinery: stable, drafted.** `PLAN.md` → "Pass-3 design record v2" holds the layer the
  PI is comfortable with: scoring (only the exam pays; zero = the strongest lazy constant
  strategy; many small weighted questions; abstain; exact-match), the smith's three gates
  (with the ZPD checked in-loop), the baseline principle (one frozen day-one smart-spec per
  lineage + an occasional bare-student sanity check), the catalog idea, the seed principles,
  student/lab/cap, the proof-of-principle milestone, and a shelf of provisional mechanisms
  that are adopted only when their failure actually appears.
- **The world: deliberately NOT settled.** Record v2 §1 (kit / components / readouts /
  switches) is one concrete instance, flagged by the PI as too specific for the principles
  layer — it reads like implementation. The PI is not yet comfortable starting from it.
  Nothing gets built until this is resolved.
- **Vision:** `ROADMAP.md` → "The gym and its chains — why taste, why this world" (preserve
  through every cleanup).
- **Docs map:** `CLAUDE.md` (orientation) → this file → `PLAN.md` record v2 (machinery,
  draft) + `ROADMAP.md` (vision). `REPLAN.md`, PLAN's v1 record, and PLAN's old staged
  passes are history — stale vocabulary in historical sections is intentional; don't "fix"
  history. The draft banners come off (= the lock) only after the world question settles,
  with explicit PI sign-off.

## The single question

**What is the right abstraction for the world — and the generative principle for creating
worlds — so the smith stays general and the PI stops being the bottleneck?**

Candidate minimal principle (a starting proposal from the closing session, not a lock): a
**planted hidden structure** (so ground truth stays checkable by arithmetic, never a judge),
**discoverable only through costly probes**, where **access compounds** (understanding buys
reach), graded **solely on demonstrated prediction** of behavior never observed. Everything
else — components, switches, readouts, even "machine" — may be instance, not principle.

Sub-questions, distilled from the PI's own words:

1. **Is the candidate principle complete?** "The abstraction is the right kind with a graph
   that's discoverable, in how research operates — is that all there is to it?" What's
   missing; what's accidental?
2. **The catalog's higher principle.** The disposition ↔ world-feature catalog (curiosity ←
   hidden doors; boredom ← diminishing veins; …) keeps becoming a hand-list. What does it
   *fall out of*, so it is endless — or at least saturable — from one principle? (Possibly
   the same answer as question 1.)
3. **Sequencing — the "two loops" idea.** Plant one maximally rich world first and let the
   inner loop run against it alone until it cracks it, bringing the smith in only later —
   versus co-evolving the smith from day one. Is planting all anticipated behaviors
   hand-design, or legitimate?
4. **The abstract-scoring thought.** Could the loop run against a more abstract (still
   non-LLM-judge) scoring — e.g. a small set of evolved situations that capture failure
   modes, improving against the growing catalog — instead of full worlds? Another chapter,
   or earlier? Would the loop even migrate there on its own?
5. **The standing meta-test.** How to maximally test the thesis (domain-general research
   taste) while never installing world-specific behavior — and how the PI stays out of the
   way ("I am doing way too much rereading because the docs got contaminated by the very
   world we wanted to plant").

## End state for that session

Settle the world principle (or honestly fail to and say where it stuck) → rewrite record v2
§1 as principle-plus-instance accordingly → with explicit PI sign-off, remove the draft
banners (PLAN.md, ROADMAP.md, REPLAN.md) — that is the lock → only then the implementation
session: build kit v1 (or whatever the settled principle's first instance is) and run the
proof of principle exactly as record v2 describes. Before finishing, run a cold-reader
subagent on any rewritten doc (it caught a real wording bug this time — zero point — and
the test is cheap).

## Settled in the closing sessions — don't reopen casually

Only the exam pays; probing earns nothing. Zero = strongest lazy constant strategy
(arithmetic, per machine) — distinct from the smart-spec, which is a live baseline rival.
Abstain earns the blind-guess credit (honesty beats bluffing; confabulation is priced, not
policed). Exact-match grading; all mercy in exam composition. Machines may be open-ended;
fairness = the budget buys real ground. Goal tracking is agent-side and for the loop to
*invent* — the score only sees earned weight. Mechanisms live on a shelf until their
failure appears. The lab obeys its own thesis: unlock, don't install.
