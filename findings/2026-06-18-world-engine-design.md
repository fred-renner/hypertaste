# World engine — design resolution (handoff)

The agreed starting position from the 2026-06-18 design session. The next session brainstorms the
build details against it (see "Open details for the next session").

## Context

World-building in this project has failed three times by **constructing** worlds (and burying them
in narrative), which re-anchors every next session and collapses either into a *fixture*
(hand-solvable, no taste) or a *story* (narrative contaminates the docs). This note resolves the
world engine at the right altitude: as an **inductive bias / constraint** under which taste-demanding
worlds *fall out* of co-evolution — **not** as a hand-authored world.

The grader is **done and frozen** (`hta/lab/scoring.py` — the `World` Protocol + exact belief-MDP
oracle/floor/score_run/grade_world). This engine *fills* it; it does not touch it.

## Plain-terms key (read first if any shorthand below is unfamiliar)

- **Grader** — the frozen scoring code (`hta/lab/scoring.py`): a dumb, deterministic function, never
  an LLM. It exposes **oracle** (the score of best-possible play — the ceiling), **floor** (the score
  of lazy, no-skill play — the bottom), **score_run** (where a real player's run lands between them),
  and **grade_world** (rates a world: is best-play far above lazy, and is it solvable within budget).
  The **band** is that floor→ceiling scale a run is placed on.
- **World** — a built world the grader reads through a fixed set of questions: what the hidden answer
  could be, which **positions** (spots) can be probed, what each costs, what a probe reveals, and
  which positions are scored. The **tableau** is the precomputed table of what every position reveals
  under every possible hidden answer — what the grader plans over.
- **Spec / declarative / safe-eval** — a world is described as **data** (a spec), never code; a
  validator + a deterministic **expander** (`build`) turn that data into a playable world. "Safe-eval"
  = the data is read, never executed, so nothing the agent writes can run.
- **The trail / the chain trick** — the one worked example, in `hta/_trail/` (a retired puzzle kept as
  a reference fixture). Its "chain trick": a position reveals nothing until an earlier one is pinned —
  how "earned access" is built without changing the grader.
- **DGM** — the evolution-loop pattern this repo already has (an archive of past versions + selection
  + a sandboxed edit step). Here the same loop runs over two kinds of "genome."
- **LOOP 1 / LOOP 2** — LOOP 1 grows the **agent** (its plain-English **playbook**), scored by live
  play. LOOP 2 grows the **world** (its spec), scored mechanically by the grader (and later by the
  live champion). They share one evolution loop.
- **Champion / ZPD** — the champion is the current best agent playbook. **ZPD** = its "zone of
  proximal development" = what it can't do yet but could with a better disposition.
- **Smith** — the world-grower (LOOP 2's generator). Proposes world **structure** only, never the score.
- **The compass** — the rule of thumb steering the smith toward worlds worth growing: push where the
  agent would learn the most *that carries*, per unit of budget, leaning toward what's uncertain. A
  guide, not a hard score.
- **Airgap** — the sandbox keeping the world's hidden answer and source out of the agent's reach
  (Direct = soft, Docker = hard); already built (`hta/dgmh/sandbox.py`).
- **MDL prior** — a mild preference for *simpler* specs/playbooks when selecting what to evolve.
- **Grader tier-up** — a deliberate, human-approved expansion of the frozen grader to handle a *new
  kind of hidden state* (e.g. instrument-building, which creates new positions at run time); rare, and
  must stay deterministic + agent-inaccessible.

## The engine (an inductive bias, not a parts list)

A world = a piece of **hidden nature**: parts with hidden wiring, investigated under a budget toward
weighted goals; what you observe is fixed by the wiring; understanding *earns access* to what wasn't
observable before. We set a small, cheaply-composable **constraint** and a smith composes freely
inside it, so taste-demanding worlds fall out. We never author worlds or specify how parts interact.

**The guardrails (the constraint), over the integrity floor:**
1. **Hidden, only-inferable wiring** → forces inference (you read effects, never structure).
2. **Compounding horizons / earned access** → multi-horizon, forward-looking allocation.
   *Encode today with no contract change* as **gated-but-present positions**: a position is probeable
   but reveals nothing (constant `observe` across hypotheses) until a prerequisite is pinned — the
   trail's chain trick (`hta/_trail/anchor.py`, `worlds.py`). Positions that *don't exist until run
   time* = instrument-building = a later grader tier-up (below).
3. **Scarcity + weighted goals** → allocation by anticipated downstream value. Two parts, **both
   leaving the frozen grader untouched**: structure-driven value-of-information (some positions pin
   many others) is already expressible; **goal-weighting is the agent's disposition (agent-side),
   never a score term** — the scorer stays uniform coverage (consistent with DESIGN.md §10).
4. **Fresh, relabeled instance every episode** → transfer by construction. The relabel changes only
   the **surface names/types the agent sees** — *not* which positions exist, their order, costs, or
   gating (those are the world's fixed structure, identical across a relabel, so the grader's
   precomputed table and its cache are unchanged). Concretely it is a presentation step in the
   play/server surface, **above the `World` object** — it must never live in `build`.

**Integrity floor (unchanged):** a dumb, deterministic, agent-inaccessible scorer (never an LLM);
evolved artifacts are **text**, realized from a validated declarative spec by a deterministic expander.

## The smith (grow the world)

- A **DGM over world-genomes** (declarative specs, safe-eval) on the shared evolution core.
- Objective is **co-evolutionary**: hunt the live champion's frontier. Variety is **emergent** — as
  the champion generalizes, only structurally-novel worlds still beat it; we do **not** impose an
  explicit quality-diversity objective (that was the superseded framing, an unfaithful proxy).
- Compass = the smith's reasoning diet: **value ≈ learning-progress × transfer, per unit cost, biased
  toward uncertainty** — not a hand-list. The old taste **catalogue** (multi-horizon, stepping stones,
  deception, following interestingness) becomes a **diagnostic** we audit against, never a build-list.
- Proposes **structure only, never the score** (re-derived mechanically).

## The bar — is a world worth keeping, and is the taste real?

**Per-world admission (cheap, model-free, every world):**
1. **The dumb-player battery (a gate, not a target).** Before admitting a world, run a few cheap
   scripted strategies on it — greedy ("grab the biggest immediate payoff"), random, sweep, a shallow
   look-ahead — and keep the world only if **best-possible play scores well above all of them**. If a
   dumb rule already nearly maxes it, there is nothing to learn → reject it. This uses **only the world
   itself — no second world needed**. It does not replace the grader's lazy `floor` (which stays the
   band's bottom); it runs *in addition*, adding smarter scripted players that best-play must also
   clearly beat — a stronger bar than the current gap-over-lazy-floor check in `grade_world`. It is a
   **yes/no admission check and a diagnostic, never a number the smith tries to grow** — tuning worlds
   to "beat greedy by as much as possible" would just breed worlds specialised against greedy. (This is
   the scripted-prober battery from the project's history.)
2. **Solvable** (already in the grader): a tasteful disposition reaches the best-play band within
   budget — so "reward uncertainty" can't breed unsolvable worlds.

**The faithful bar (the real one):** the **live champion's zone of proximal development** — this
champion can't play the world well yet, but a better disposition could. Only the live student can say
this; no cheap stand-in is trustworthy.

**Cheap guards that the grown taste is general (per iteration):** fresh relabeled instances (nothing
memorisable survives), and **you and I reading the grown playbook** for whether it reads as a general
way of working or a trick tied to one world (read-only — never a selection target).

**The strong generality test is deferred (occasional, far-lookahead):** whether the taste carries to a
*different kind* of world — and ultimately to a real problem — is the genuine transfer / field test. It
needs other worlds, so it is **not cheap and not per-iteration**; treat it as a rare check, not a gate.
Out of scope for getting the loop turning.

## The hub

**One evolution core, two genomes.** The core (archive + open-ended quality×novelty selection + MDL
prior + sandbox airgap) is already built and genome-agnostic.
- **LOOP 1** — task-agent **playbook** (text). Evaluated by live play → `score_run`. Cents/episode.
- **LOOP 2** — world **spec** (declarative data). Evaluated by mechanical `grade_world` + the
  dumb-player battery (free), then the live champion.
- Shared: archive, sandbox, meta-edit orchestration. Divergent: the artifact, the evaluator, the
  meta-instruction. **Asymmetry respected:** the player is graded by the world; the world is graded by
  the grader (+ champion) and **never reaches the score**; both genomes go through the airgap; the
  grader is model-free.

## Build order

1. **Static hidden-nature first** — prove the loop can grow *something* that reads as taste, with the
   fewest moving parts.
2. Then **instrument/experiment-building** as the next axis — **confirmed a grader tier-up** (new
   observable positions at run time contradict the fixed `positions()` contract), opened deliberately
   on the machinery once static works.
3. The grader otherwise stays **frozen**; it grows only by deliberate, human-gated **tier-up** when a
   new *kind of hidden state* is needed, and any replacement must stay deterministic + agent-inaccessible
   (a movable score is a hackable score).

## Seed

- **Decently complex** — the smallest world that *genuinely demands multi-horizon allocation under
  scarcity*, **not** "3 boxes, be tasteful in 3 probes" (that's a fixture by construction).
- Seed champion playbook = **"be a tasteful researcher, understand/solve the world"** (deliberately
  under-specified — room to grow).

## What the landed code already gives (do not rebuild)

- **The entire grader** (`hta/lab/scoring.py`): oracle/floor/score_run/grade_world ride any `World`;
  the oracle is lru-cached on the *tableau*, so relabeled-but-identical instances share the cache.
- **The shared evolution core**: `hta/dgmh/archive.py` (quality×novelty selection + MDL prior,
  genome-agnostic), `hta/dgmh/sandbox.py` (Direct + Docker airgaps, fail-closed).
- **The safe-eval seam**: `hta/world/spec.py` `validate`/`build` (structure in place; body stubbed).
- **Config gates**: `hta/config.py` (`world_gap_min`, `world_reach_min`, models, MDL λ).
- **The worked example**: `hta/_trail/` — the chain trick (earned access with no contract change) and
  the forked-spec structural family to generalize from (narrative-stripped).

## Open details for the next (build) session — the blocking unknowns

- **Composition grammar** (critical path): how hidden nature is declared as a cheaply-composable spec
  (part vocabulary + wiring rules) + the deterministic expander (`validate`/`build`). Generalize from
  `hta/_trail/worlds.py`, narrative stripped.
- **Seed spec** in that grammar (co-constrains the grammar).
- **Relabeling scheme** (above `World`, in the play surface; what permutes vs invariant; per-episode
  seed→map).
- **The dumb-player battery**: the exact scripted strategies (greedy, random, sweep, shallow
  look-ahead), how far best-play must beat them to admit a world, and where it plugs into the ship-gate
  (kept out of the smith's compass). Builds on the existing lazy `floor`.
- **Smith mutation operators** on the spec + its airgapped edit instruction.
- **Compass proxies**: a concrete learning-progress signal (a cross-episode delta the archive does not
  store today) and a concrete transfer metric (the deferred field test is the honest one).
- **Structural-signature diagnostic** (for auditing emergent variety; descriptive, not an objective).

## Traps to keep guarding (each has bitten this project before)

- **The trivial world.** If a simple rule already plays a world near-perfectly, the agent learns a
  trick, not taste. *Guard:* the dumb-player battery above — keep only worlds where smart play clearly
  beats dumb play.
- **The story creep.** Naming a world with a story ("a trail through mines…") quietly re-anchors the
  next session to that story and the design drifts. *Guard:* name and describe worlds by **structure**
  only, never a narrative.
- **The fake difficulty meter.** Any cheap stand-in for "this world demands taste" — a fixed heuristic,
  a difficulty number — eventually misleads, because the only honest judge is the actual agent we are
  growing. *Guard:* cheap checks **filter** worlds; only the live champion **certifies** that a world
  sits in its learning zone.
- **The prompt is not the lever.** Re-wording the agent's instructions does not grow taste; what has to
  grow is **structure the agent builds** — notes it writes down, how it breaks a problem apart, checks
  it runs on itself. *Guard:* judge the playbook on the procedure it carries, not its phrasing. (A
  LOOP-1 concern, noted so it is not forgotten.)
- **The cozy rut (grower–solver collusion).** Left alone, the world-grower and the agent can settle
  into a comfortable loop where the grower only ever pokes this agent's current blind spot and neither
  gets more general. *Guard:* fresh relabeled worlds, push the grower toward what carries, read the
  playbook for narrowness — and **watch for this happening rather than assume it won't**.

## Verification (how the eventual build proves out)

- The loop **turns offline/free first** (static nature, mock backend, deterministic spec mutation):
  seed → smith mutates → battery + `grade_world` admit/reject → archive.
- Then a **live thin slice** (cents): the champion plays the seed; `score_run` places it in the band.
- **Taste check**: humans read the grown playbook (general way of working vs world-specific trick); the
  champion improves on fresh worlds it was not bred against; the port check (same playbook on a
  different model) holds. (The strong transfer / field test is a later, occasional check, not a gate.)
- **Integrity**: no `hta.llm` import under `hta/lab/`; the relabel lives above `World`; the smith never
  writes a score.
