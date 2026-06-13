# PLAN — the redesign lock + staged passes

Locked 2026-06-10 (the post-worldsmith brainstorm). This is the working contract for the
redesign: what is settled, what gets built in what order, and what stays open. It supersedes
the "Next action" sections of `CLAUDE.md`/`RESET_DESIGN.md` for sequencing; the two invariants
and the locked decisions of the reset still stand except where this document explicitly moves
them (the plodder, the virtue battery, the body ring).

## The definition and the thesis

**The definition (settled 2026-06-13, see `PASS3_REDO.md`).** Taste is choosing your next move
well by evaluating your position.

**The thesis (why grow it — the portability claim).** Taste is the situational trigger, not the
capability. The model can already make every move (abstract, falsify, delegate, commit); what
separates good inquiry from lazy inquiry is the operating procedure that fires the right move
when the position calls for it — so in principle you could equip even a weak model with it. We
grow that procedure, measure it objectively (against the same model without it), and ship it.

## The three layers (vocabulary, so it stops being slippery)

- **The lab** — the outer machinery: loop, archive, world-smith, scorer, airgap. Grows and
  measures taste. Never shipped, never evolved.
- **The body** — the fixed capabilities the harness offers the player: probe, spawn, memory,
  submit. The agent's hands.
- **The operating procedure** — the evolved English: how the agent drives its body (when to
  spawn, how to keep notes, which bets to make, when to stop). **This is the product.** It is
  a harness, written as a procedure instead of as wiring. The weak player (Haiku) is only the
  test rig; the procedure is ported onto strong models and, eventually, real domains.

## The three rings (what may change, and by whom)

1. **Frozen — the constitution.** The scorer, the judge, the airgap. Objective,
   agent-inaccessible, never an LLM, never in any search space. (A movable score is
   wireheading; this ring is what keeps the project science.)
2. **Ratified — the body.** The loop may *propose* body changes when the evidence points at an
   affordance limit (a different hierarchy, finer memory ops); proposals surface in the run
   artifacts and are applied only by the PI. The body never changes mid-lineage silently —
   it is part of the measurement instrument.
3. **Free — the operating procedure.** The only thing the meta agent edits. English, read as
   context, never executed. Within an episode the player may compute freely over what it
   probed (that is capability, not the carried artifact); what is distilled and carried
   forward stays text.

## The design lock (settled this session — don't reopen)

1. **World = a hidden map discovered by probing.** The *topology* is hidden, not just values
   on a public graph. Probes reveal pieces of the shape; betting becomes **informed but never
   certain** — you act on hunches, not deductions, which is what keeps the optimal policy
   tacit (solver-proof) while ending the blind-betting flaw of the switch worlds.
2. **Multiple horizons (coupling) are the soul.** Cheap probes that pay nothing now but
   unlock downstream regions make stepping-stones and learning-gradient-following
   *instrumentally correct on the single objective*. Drives (curiosity, "fun" = staying on
   the learning gradient) are never score terms — the world makes them pay, or they don't
   exist here.
3. **Multiple goals** with agent-chosen dynamic weights, rolling up into one objective
   outcome. The weighing-between-goals (and the stepping stone, whose value is unknowable
   when taken) lives here. Interface is first-class from day one; lit up after the loop is
   green (Pass 6 — committed, not optional).
4. **Scoring: band against best-play alone.** Best-play = the optimal player *under
   uncertainty* (not omniscient), computed mechanically by the lab. The plodder is deleted as
   a runtime baseline; its one job (strip free coverage) moves into the build-screen: a world
   ships only if no-inference coverage ≈ 0.
5. **Generic interface everywhere — the generality sieve.** variable/value, cells/links/
   budget/coverage; zero world-story in anything any agent sees (player tools, world_map,
   meta prompt, inventor prompt, reports). If the player can't see the container, it can't
   overfit the container. This is also the plug-and-play bridge: a synthetic map today and a
   real domain tomorrow implement the same interface.
6. **The world is the gym, not the game.** Its only job is clean measurement (computable
   best-play) plus tacit room (best-play not articulable). The end-state is the port: grow
   the procedure in the gym, transfer it to real problems (codebase, black-box system,
   simulator). The gym never has to *be* research; it has to build muscles that transfer.
7. **The world-smith searches; the virtues are discovered, not installed.** It searches a
   rich world-grammar for structures where the *live* champion fails (the ZPD, on the
   non-movable scorer), and the failure-modes it finds *are* the virtue list. Our
   hand-reasoned battery (allocation, deception, commitment, abstraction-when-needed, …) is
   demoted to a **private validation checklist** — did the loop rediscover these and find
   axes we never named? — never fed to any agent.
8. **Situations are a first-class instrument.** A situation = a constructed mid-episode state
   (partial map, scratchpad, remaining budget): cheap, deterministic, targeted at one
   trigger. Used for (a) the world-smith's ZPD checks against the live champion, (b) fast
   filtering of meta-edits before they earn a full eval, (c) the validation battery. Full
   hidden-map episodes remain the exam — context/memory pressure only exists there, and a
   procedure tuned only on a situation library would overfit the library.
9. **Run artifacts live in the repo.** Archive lineage, playbooks, sanitized reports,
   accounting, and a cheap visualization of the player's trajectory on the map. A run you
   can't inspect didn't happen.

## The staged passes

Free offline gate between every pass (`pytest` costs zero tokens — only `--backend real`
spends money; live runs appear exactly where they are the point). The current anchor world
stays in place as the canary until the new world replaces it — we refactor on it, we don't
invest in it.

> **Note (2026-06-11, record v2 below):** Passes 3–6 are reshaped — every world axis is
> named in the kit's design from day one and opened by the gated smith (axes, not passes;
> the kit itself is implemented in slices, starting minimal); Pass 6 dissolves into the
> multi-goal axis.

- **Pass 0 — safety net + artifacts.** Tests green; persist a curated run (archive +
  transcripts + accounting) into the repo; un-ignore the artifact path. *Gate: a sample
  run's artifacts land in-repo and are readable.* **Done 2026-06-10:** the loop now writes
  `iter_*.json` (full transcripts + hidden draws, replayable) and `run.json` (accounting)
  next to the archive; `runs/` un-ignored; sample at `runs/sample-mock/`; 67 tests green.
- **Pass 1 — delete the provably dead.** `hta/meta_agent.py` (the Chapter-1 meta agent —
  Chapter 2's lives in `loop.meta_edit` + `hta/sandbox.py` and **stays**), the dead halves of
  `taste.py` (Ch1 fitness/metrics), the inert config weights (`w_solve`/`w_approx`), stale
  doc references that call dead code "the spine". Verified by import graph first. *Gate:
  tests green; nothing dead described as live.*
- **Pass 2 — generic interface, on the canary.** register→variable, color→value; strip
  trail/valley/clearing narration from `world_map`, tool docs, kickoff, meta prompt,
  reports; re-seed the playbook to one genuinely-general line (the calibration leak comes
  out). *Gate: tests green; mock run identical; one live smoke episode works.*
- **Pass 3 — the hidden-map world.** Opens with its own **design brainstorm** (see open
  questions — the computability question is first). Then: 3a the spec + best-play +
  build-screen (free, model-free; the screen now also enforces no-free-coverage ≈ 0 and
  solver-proofness); 3b wire into the harness (small — the substrate is already generic over
  a spec protocol) + the situation harness (start an episode from a constructed mid-state) +
  the trajectory visualization. Multi-goal interface present but off. *Gate 3a: build-screen
  passes. Gate 3b: mock loop + one live smoke episode on the new world.*
- **Pass 4 — re-prove the inner loop, live + calibrate.** A few live iterations on the
  hidden-map world. Held-out = fresh topologies **by construction** (every draw is a
  different shape — the generality signal is the exam now, not an extra container). Wire the
  MDL/length prior on the playbook at selection (currently dead code) — prices verbosity,
  nudges structure-over-prose. Watch for structure emergence in the scratchpad/playbook
  (the dynamic goal-weight table); if absent, make the failure legible in the report, never
  install the schema. *Gate: held-out coverage climbs; the grown procedure reads general;
  cost within budget.*
- **Pass 5 — the world-smith as a real searcher.** The inventor proposes world-grammar
  structure as validated data (no more hand-authored moves, no more hand-written proxy
  policies as the answer key). Ship-gate = mechanical hard/solvable + **live-champion
  fails** (situations make this cheap). The coach gets quality control: a child must beat
  its parent on the situation battery before earning a full eval; a second coaching round is
  allowed when the first regresses. *Gate: it authors a world/situation the live champion
  fails that we did not hand it; one full two-loop iteration live, graduate carried
  forward; the virtue-discovery validation starts recording.*
- **Pass 6 — light up multiple goals (committed).** Competing goals, agent-weighted, one
  objective rollup. The allocator, stepping stones, and goal-switching become measurable.
  *Gate: loop runs; weighing visible in conduct; the score stays unmovable.*
- **Pass 7 — consolidation refactor.** Now that everything is in, restructure the code to
  the converged architecture (kill the Frankenstein accretion; the module map should read
  like the three layers). *Gate: tests green; a live smoke run unchanged.*
- **Pass 8 — docs collapse (last).** Rewrite README/CLAUDE/design docs to the final state.
  Rule: preserve the genuinely interesting reasoning as archived history (NOTEBOOK), cut the
  false present tense. PLAN.md folds into the design record.
- **Periodic, from Pass 4 on — the port check.** Drop the current champion procedure onto a
  *different* model for a few episodes. If it only helps Haiku, we grew Haiku-whispering,
  not a procedure. Cheap; it is the thesis test.

## Pass-3 design record (locked 2026-06-10 — the brainstorm's outcome; Q1-Q4 answered)

> **Superseded 2026-06-10 (the PI conversation) — see `REPLAN.md` and record v2 below.** The hidden-map world
> sits below the threshold gate (public lattice → the optimal policy is articulable); it is
> demoted to an offline regression fixture. This brainstorm is redone as a PI session,
> starting from `REPLAN.md`, which also moves design lock 4's oracle band to an empirical
> band. The record below is kept as history.

**The grammar (`hta/ch2/hidden_map.py`).** A world is a set of node GROUPS plus one shared
backbone. Each group: an entry, public layers of candidate successors, and one hidden realized
path — which candidate each node links to and where it stops (the hidden depth). Hidden
variables: (path, key) per group + the backbone — a product of per-variable ranges, so the
family is public and enumerable (capped at 4096) and best-play stays the exact belief-MDP by
simulation: **Q1's answer** — topology variables are just variables with ragged ranges, riding
`anchor.py`'s machinery through a three-point protocol extension (`hypotheses`, `value`,
`PROBE_KINDS`/`COV_KINDS`). Probe cells: links (a node's place on the realized path: off / stop
/ next), one key per group, the backbone. Coverage cells: regions, inference-only — value =
(key + backbone + path_length + pos) mod 2, backbone only when coupled. Probeable and coverage
are disjoint, so the no-inference floor is exactly 0 (design lock 4 enforced by construction);
the band is 0 -> best-play. The LENGTH term keeps the deep payoff strictly beyond a 2-move
horizon (no key+backbone shortcut); a layerless uncoupled group is the 1-probe bait.

**Q2 (coupling):** the backbone — one cheap probe that pays nothing alone and unlocks the last
mile of every coupled region; the dial is how many groups couple and their region masses.
**Q3 (discovery pressure):** the candidate lattice is public, the realized edges/depth hidden —
every draw is a different shape, so held-out generality is by construction (Pass 4's exam).
**Q4 (drills vs exam):** the harness is built (`hta/ch2/situations.py` — prefix probes replayed
through the ordinary probe path, scratchpad pre-seeded, scored against the situation's own
best-play-continuation band); the mix policy is decided in Passes 4-5.

**The canonical world** (`canonical_spec`, screened by `run_hiddenmap.py` — controls separate,
7/8 sweep rows ship, the no-mid control correctly holds): one deep coupled group (depth 1..3,
region 8), one mid coupled group (depth 1, region 5), two baits (region 2), budget 6. Gates:
floor 0; best-play 15.86 vs best generic planner 9.0 (gap 0.43n, room 0.57n); the articulable
reference method (backbone -> key -> pin depth by probing links DEEPEST LAYER FIRST, an off-path
read killing every deeper shape at once) reaches best-play exactly — solvable; cliff 0.47.

**Faithful to the live student** (the 2026-06-09 finding, enacted): the pointer chase is
probe-mediated — the world answers every hop, so mis-resolution cannot happen silently in-head;
reconstruction at submit is one line of arithmetic; coverage is four mid-size regions, never one
all-or-nothing valley. **Gate-3b live smoke (2026-06-10, $0.10):** seed-playbook Haiku played
coherently — all keys + backbone + one link, resolved the mid group and both baits, submitted
exactly what it earned (raw == determined: the reconstruction pathology is gone) — 0.57n,
landing precisely at the generic-planner mark with the whole taste gap above it. Multi-goal:
`goals()` present, off. The trajectory renderer is `hta/ch2/trajectory.py` (design lock 9).

```bash
python run_hiddenmap.py                         # the Pass-3 build gate: free, model-free (~2 min)
python run_hiddenmap.py --smoke [--backend real]  # one episode + trajectory (real: cents)
python run_loop.py --world hidden --backend mock  # the loop on the new world, offline
```

## Pass-3 design record v2 (drafted 2026-06-11, revised 2026-06-12 after the PI reread — pending final PI read; ratifies REPLAN.md, supersedes the v1 record above)

> **Status: draft — not locked until this banner comes off (explicit PI sign-off).** Outcome
> of the 2026-06-11/12 PI sessions. The machinery layer (§2–§7, the milestone, the shelf) is
> stable; **§1's world is one concrete instance, not the settled abstraction** — now resolved in
> `PASS3_REDO.md` (the taste definition, the rules of the game, and our world as one instance;
> fold it in here on the lock). The record is layered on purpose:
> **Principles** are the bets we expect to survive; **Provisional mechanisms** are defaults
> on a shelf, each adopted only when the failure it guards against actually appears. The
> lab obeys its own thesis — unlock, don't install — for its own machinery too.

### Principles

**1 — The world: a hidden machine, assembled from a kit.** The lab owns a **kit**: a small
set of component types (formulas, lookup tables, switches) plus assembly rules. Per episode
it assembles a hidden **machine**: a directed graph of components, each computing its value
from its parents. The agent sees none of this. It sees only the machine's surface:
**inputs** (root nodes — some **settable** by the agent, some **nature-driven**: the world
sets them on its own seeded schedule and the agent can only watch) and whichever components
have a **readout** (a channel making that component's value directly readable). Everything
else — wiring, component types, shared hidden values, even how many components exist — must
be inferred by probing. Difficulty, here, is simply how much is hidden and how hard it is to
reach; two dials: **control** (how many inputs are settable — experiments at one end,
astronomy at the other) and **readout coverage** (how much of the middle is directly
readable).

- **Access is earned.** Some readouts are dark (visible but dead until the machine is
  driven into the right condition) or unlisted (nothing advertises they exist until woken —
  the Neptune case: only a misfit in the visible region hints at them). Switch components
  route what is connected to what. The setting that opens a locked region is always
  inferable from what other regions teach — never a brute-force secret. The map the agent
  grows is its charted subgraph; often one region's understanding is the instrument for the
  next, and some regions are dead ends on purpose.
- **Machines may be open-ended** — larger than any budget can fully pin. Fairness requires
  only that the budget can buy real ground (a meaningful share of the exam reachable);
  beyond the reachable frontier, honest abstention is the right answer.
- **The seed family starts static** — probing is reading; every answer is a permanent fact.
  Machine memory (state; equivalently, feedback loops in the graph), noise, low control,
  hidden probe costs, planted literature, and instrument-building are axes the **smith**
  opens through its gates whenever the champion is ready — named here only so the
  architecture accommodates them; the kit is implemented in slices, starting minimal.

**2 — Scoring: the exam, and only the exam.** Probes spend budget and earn nothing. At
episode end the lab asks a set of held-out questions — fixed per machine and identical for
every player on that machine (tailoring the exam to an agent's path would break paired
comparison), phrased in the same flat vocabulary as probes ("what does output o read when
the inputs are set to …?"), drawn from a space far larger than the budget so memorizing
one's own probes cannot pay. Exam size scales with machine size — a calibration output,
like every other constant.

- **Zero = the best blind guesser.** From the answer key the lab computes the strongest
  *lazy* strategy — one fixed answer per output, applied across the whole exam (not per
  question: a per-question "best constant" would just be the answer key); skill is scaled
  above that (lazy or all-abstain = exactly 0, wild guessing < 0, perfect = 1). The
  normalization is for readable reporting — every decision is a paired comparison on
  identical machines, where the zero point cancels.
- **Many small questions, none dominant.** A question's weight grows with how much hidden
  machinery sits upstream of it, more again behind a lock — computed from the wiring (e.g.
  weight ∝ the number of hidden values upstream of the asked output: legible, cheap,
  scales). How much weight rides on any single hidden
  value is a watched statistic, not a fixed cap. One cruel jackpot question is how the old
  hedge pathology was born; it is outlawed by exam composition, never by softer grading.
- **Abstain is allowed**, worth exactly that question's blind-guess credit. It never beats
  knowledge, only wrong confidence — and on questions beyond the reachable frontier it is
  the *correct* answer, so knowing the edge of one's own map is scored without a judge.
- **Grading is exact-match and dumb.** "Close counts" grading would reward middle-value
  guessing (the hedge reborn as arithmetic). All mercy lives in the exam's composition;
  none in the grader. Confidently-almost-right ≈ wrong is how nature grades.
- **Goals need no ledger.** A multi-goal machine is one with regions of different richness;
  the exam covers the whole machine. Choosing goals *is* allocating budget; the choice pays
  through the weight actually earned and is visible in the probe log. No claims, no weight
  declarations, nothing to game. Competing goals themselves are wanted (the human analogy
  stands) and live in the world; how the agent *tracks and weighs* them mid-episode is for
  the loop to invent — watched for in artifacts, never installed. The score only ever sees
  earned weight. (The goal-ledger scoring of the first draft is dropped.)

**3 — The smith and its gates.** The smith's inventor (a strong model) proposes the next
world as a **parts-list and wiring diagram in a fixed format** — data the lab validates and
assembles itself; model text is never executed. Three gates per world:

1. **Too easy?** Scripted probers (random pokes; sweep-and-fit) must score ≈ 0. These are
   free unit tests of the world, run at build time — QA on the world, not baselines for
   the agent.
2. **Fair?** Verified by construction: every component type in the kit carries its
   identification recipe (e.g. "an affine part is pinned by three probes"); the builder
   sums recipes in prerequisite order and confirms the budget buys a meaningful share of
   the drawn exam's weight (the question *pool* is huge so memorization can't pay; the
   fairness check is about the exam actually drawn).
3. **In the ZPD?** Only reality can answer whether the live champion fails here, so the
   world's first loop iteration *is* the check: champion fails, the coach gets a few
   rounds; no fix ⇒ the world returns to the smith. Any pre-loop stand-in for the student
   is a model of the student — the unfaithful-proxy trap that forced this redesign. The
   only coupling between smith and student is the objective gap on the unmovable score.

**4 — The baseline principle.** One standing baseline per lineage: the **smart-spec null** —
the best day-one playbook the lab's strongest model can write, frozen at lineage start and
never rewritten mid-lineage; comparing against it later just means running it (cents). The
claim under test is always: *the evolved procedure beats the best day-one procedure on
fresh machines, same student, same body.* The bare student (no playbook) is checked
occasionally — is a playbook net-positive at all, or are we installing nonsense in the way
of decent behavior? We need a clear signal relative to the baseline, not a fortress of
proof.

**5 — The catalog (the evolution move).** Never install a disposition in the score or the
seed; build the world feature that makes it the winning strategy across fresh draws, and
let selection write it into the playbook. Habits so far: curiosity ← hidden doors; boredom ←
diminishing veins; the anomaly itch ← regime switches; calibration ← hidden exam + abstain;
stopping ← the budget; externalizing ← episodes longer than working memory;
persistence-vs-sunk-cost ← mixed walls (some have workarounds, some are true dead ends);
replication ← noise; trust of sources ← planted literature (incomplete, occasionally
wrong); cost sense ← hidden probe prices; instrument-making ← regions with no readout that
a rig composed from already-pinned parts could read ("creating something that lets you
create a meter"); abstraction ← regions that stop yielding to enumeration and only yield
to a compressed law (one trigger among several: mapped-but-stuck). One row lives at the
meta-level rather than in any world: **learning from others** — coaching and the archive
*are* cultural transmission; the loop itself is that row. Open (next session, `NEXT.md`):
the catalog must not remain a hand-list — name the higher generative principle it falls
out of. **World-side only:** the inventor may read the catalog; coach, player,
and playbook never — or the rediscovery test (did selection find curiosity unprompted?) is
contaminated. New component types are code, so they arrive through us — deliberate and
logged, made routine by the **wish channel**: inventor wishes are inert text surfaced in
lineage reports, never read back by the loop.

**6 — The seed world (principles; every constant is a calibration output, frozen per
lineage).** A handful of components; chains two or three deep; one shared hidden constant
(transfer between regions exists from episode one); one gently locked readout (earned
access exists from episode one); stateless; full control (nature-driven inputs are a later
axis); a single goal region (multi-goal likewise later, smith-opened); uniform probe
costs. Too easy ⇒ extend from the kit on day zero; gauging is iterative.

**7 — Student, lab, and the cap.** Lab roles (coach, inventor, smart-spec author) run the
strongest available model, locked and recorded per lineage. The student stays weak (Haiku)
on purpose: on a weak engine any horizon extension is attributable to the procedure, not
the engine — never promote it. The playbook is capped (~350 words, the seed included) so
every addition costs a deletion — insurance only: the real force against overfit rules is
that **every eval draw is a fresh machine**, so a rule keyed to one observation cannot pay
twice. The within-episode scratchpad is never capped.

### The proof of principle — the next milestone, before any further machinery

**Kit v1 is the new world** (the graph-of-components machine above); the old anchor and
hidden-map worlds survive only as offline regression fixtures. Smallest honest slice: two
or three stateless component types (formula, table, switch), settable inputs, builder +
exam + scripted QA. One seed family. The experiment, in order: scripted QA green (free);
the bare student on a few fresh machines; the student with the frozen smart-spec; a few
coaching iterations. **The signal sought: the evolved playbook visibly beats the frozen
day-one playbook on fresh machines.** Cost: a few dollars. If the signal exists, mechanisms
come off the shelf as the loop's real behavior demands them; if it doesn't, we learned the
core bet is in trouble before furnishing the house. The implementation session settles the
remaining how-exactly questions (component formats, the exam-drawing algorithm, the probe
interface, calibration constants) — this record fixes the what and the why.

### Provisional mechanisms (the shelf — sketches; each specified and adopted only when its failure appears)

- **Promotion statistics**: a pre-registered paired rule, sample size set from observed
  noise — for when eval noise actually starts fooling us; until then, "visibly beats" on
  paired draws decides.
- **Standing controls**: the renamed twin (a structure-preserving relabel of the same
  machine must show zero gap — a leak detector); the re-rolled draw (same blueprint, fresh
  instance — the noise estimate); the scalar crank (size-only changes must not reopen
  gaps — a regression test of the old "no scalar dial reopens the gap" finding).
- **The near-miss sweep**: change one hidden value at a time and check the builder's plan
  would notice (the exact version of fairness checking and question weighting) — an
  offline debugging tool for suspicious worlds, not a standing gate.
- **Transfer thermometers** (from mid-lineage; always invisible to selection, or Goodhart
  kills them): the alien-family audit (a small task family the kit did not generate); the
  planted-bug canary (a fault we plant in a real codebase — real substrate, plantable
  truth, dumb pass/fail); the leak watch (method vocabulary in playbooks is the goal;
  machine-internals vocabulary is a leak); the port check (the champion playbook dropped
  onto a different student model — the thesis test).
- **The exhaustion signal**: several smith candidates in a row already solved by the
  champion ⇒ "the kit may be the bottleneck", flagged in the lineage report.
- **Chapter-close criteria** (defined when a chapter actually runs long): the
  champion-vs-baseline gap plateaus across consecutive shipped worlds + the smith stops
  finding shippable ZPD worlds + the port check holds.
- **Goal bookkeeping affordances** — only if multi-goal play turns out to need them.
- **Later kit axes** (named in §1): machine memory, noise, nature-driven inputs, planted
  literature, heterogeneous probe costs, instrument-making.

### What this supersedes

The v1 record above (hidden-map world → offline regression fixture). Design lock 4's
oracle band (→ the empirical baseline of §4). Design lock 1's "family public and
enumerable" (→ open from the inside, planted from the lab side). Pass 6 as a calendar
event (→ the multi-goal axis, smith-opened). The goal-ledger scoring of this record's
first draft (→ earned weight, §2). Everything else stands: the generic interface,
situations as instrument (drills for agents: replay a recorded probe log with an empty or
champion-grown scratchpad, never a hand-written one — distinct from the scripted QA
probers, which test worlds), run artifacts in repo, and the two invariants.

## Open questions (the v1 Pass-3 brainstorm — answered or dissolved by record v2 above; kept as history)

1. **Computability first:** with hidden topology the hypothesis space is topologies ×
   values. The constraint that keeps best-play exact: the *family* is public and small
   (enumerable by the scorer), the *instance* hidden. What grammar gives rich shapes under
   that ceiling?
2. **The coupling dial:** small threads + a thin shared backbone (cheap best-play, real
   multi-horizon inference). No clean theory — tuned by watching the gap. Too independent =
   a budget-split with no inference; too coupled = the oracle explodes.
3. **Discovery pressure:** how much topology is hidden vs. given (note: this is *not* an
   abstraction dial — abstraction is a move over what you already hold).
4. **Situation library vs. full maps:** the mix per iteration (drills vs. exam).
5. **When exactly multi-goal lights up,** and what the minimal two-goal world looks like.

## Honest risks

- **The coach is the weakest measured link** (the live run's finding: precise diagnosis,
  regressive edit). Mitigations are wired into Pass 5 (situation-battery filter, second
  round); if coaching still regresses, that — not the world — is the next redesign.
- **Eval noise eats the gradient** if unbudgeted (stochastic weak player, small n). Paired
  seeds, repeats where they matter, deterministic situations as the low-variance instrument.
- **Best-play blow-up** under hidden topology — mitigated by the small-family constraint
  (open question 1); if it still explodes, fall back toward more factoring and re-grow the
  coupling.
- **Cost:** the ~31k-token tax × call count is the whole bill. Every gate that can be
  model-free is; staged eval (situations before full evals) guards the rest; the oracle is
  free by construction.

## What we deliberately did NOT change

- The two invariants (objective agent-inaccessible scoring; carried artifact is text).
- Opus invents/coaches, the weak model plays; probes (cost), not turns, bind.
- The airgap mechanics (tool confinement; world source unreachable from any agent surface).
