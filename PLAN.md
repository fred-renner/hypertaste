# PLAN — the redesign lock + staged passes

Locked 2026-06-10 (the post-worldsmith brainstorm). This is the working contract for the
redesign: what is settled, what gets built in what order, and what stays open. It supersedes
the "Next action" sections of `CLAUDE.md`/`RESET_DESIGN.md` for sequencing; the two invariants
and the locked decisions of the reset still stand except where this document explicitly moves
them (the plodder, the virtue battery, the body ring).

## The thesis (the one sentence everything serves)

**Taste is the situational trigger, never the capability.** The model can already make every
move (abstract, falsify, delegate, commit); what separates good inquiry from lazy inquiry is
being equipped with the operating procedure that fires the right move when the situation
demands it. We grow that procedure, measure it objectively, and ship it.

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

## Open questions (the Pass-3 brainstorm, before anything is built there)

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
