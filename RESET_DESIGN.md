# Chapter-2 reset — the design we locked (decision record)

> **Superseded 2026-06-13 — kept as history.** This is the anchor-trail chapter. The current
> design is `PASS3_REDO.md` (the taste definition, the rules any world must meet, and this
> probe-world demoted to *one instance*, not the world). The locked decisions here — English
> playbook, model-orchestrated, objective scoring, the airgap — still hold; the specific world
> and its mechanics are now a regression fixture. Don't treat this file as current.

This is the forward design from the session that followed the "harness writes the oracle"
finding (`NOTEBOOK.md` → "The harness substrate"). It supersedes the Chapter-2 *mechanics* in the
archived `NOTEBOOK.md` (the slice-by-slice lab history). Read this first.

The one-line problem it answers: every Chapter-2 world so far slid **below threshold** — some
agent in the loop (Haiku reasoning in-head, then Opus writing a brute-force solver) could just
*solve* the world instead of needing grown, tacit taste. The fix is two coupled moves: pull the
evolved artifact **out of Python and into English**, and build a world where the **content** of
the winning policy is learnable only by playing, never derivable from the public structure.

## Locked decisions

1. **English artifact.** The evolved unit is **non-executable natural language** (a playbook),
   never code. Rationale: it is the operational definition of the thesis — taste = the *tacit,
   non-algorithmic residue* of good inquiry; an algorithm is articulable capability Opus already
   has. English-only is the sieve that keeps the residue and discards the capability, and it makes
   **model-generality the test** (a Python solver lifts every model to 100% by ignoring it; an
   English disposition only helps if it routes through the model's reasoning). **Open in extent**
   (any English structure the meta agent likes), **closed in kind** (the harness reads node files
   as text context only — never imports or executes them; safe-eval, lifted).

2. **(B) the model orchestrates.** The top-level is a **Haiku agent** whose system prompt *is* the
   evolved playbook; it natively decides to spawn workers, hold within-episode memory, and submit.
   *Not* Python orchestrating model probers (that was option A / today's harness, and it is what
   let taste compile into a solver). The allocator is emergent model behavior guided by English.

3. **Tool confinement is the airgap** — not Docker-per-spawn. The hidden state lives in the probe
   server's process; every player session is confined by allowlist to {probe, spawn, memory,
   submit}. No Bash, no filesystem, no general Task. Docker becomes optional defense-in-depth at
   the *episode* boundary (one container per episode at most), never per worker.

4. **Two planes, opposite tool policies.**
   - **Meta agent (Opus)** — *invents structure*. Full edit tools on the node; never touches the
     world; gets a sanitized report. This is the "give it all tools" plane.
   - **Player (Haiku)** — *enacts* the playbook on the world. Confined as above. Its confinement
     is the airgap.

5. **Memory is a within-episode tool; generality lives in the playbook.** Episodes are
   independent. The notebook is the top's working store for ONE world (integrate worker reports,
   build the map, track/ revise hypotheses) and **resets per episode**. "Accumulated play" happens
   in the **loop** — the meta agent distils taste into the playbook across iterations — not in a
   player-written notebook across episodes. Memory affordance: an **editable scratchpad** with
   **incremental patch** ops (not full-replace, not append-only), so compression/forgetting/
   buffering are reachable. **Provide the capability, withhold the schema** — the structure
   (buffered, slotted, …) is for the loop to invent, like the allocator. *Where the invented
   structure lives:* the **schema is note-keeping discipline written into the playbook** (it is an
   instruction — English — so it belongs in the one evolvable node); the scratchpad is its
   per-episode instantiation. A "smart memory system" is an evolved **protocol**, not a persisted
   data structure — which is why `playbook.md` as the only evolvable node suffices.

6. **The judge is unchanged (integrity floor).** Coverage, normalized into a model-free
   floor→oracle band, deterministic and agent-inaccessible. References by **verified simulation
   over the family** when closed-form gets fragile.

## The harness spec (the substrate to reseed)

**Fixed substrate (frozen Python, not in the search space):** one probe-MCP server per world
(holds the hidden state, global budget); the orchestration primitives; the allowlist airgap.

**Tools**

| Tool | Signature | Who | Notes |
|---|---|---|---|
| `probe` | `(index) -> {value, remaining, cost}` | top + workers | draws from the global budget (cost-weighted) |
| `submit_map` | `(values) -> ok` | **top only** | ends the episode |
| `spawn` | `(task:str, budget:int) -> {observations, report, used}` | **top only** | ONE **fresh** worker: sees only {task, probe tool, its budget}; no top context/playbook/memory. `budget ≤ remaining`, unused returns. Depth = 1 in the seed. |
| `world_map` | `() -> public structure` | top | the known rules of the game |
| `remaining` | `() -> int` | top + workers | global probes/budget left |
| `mem_read` | `() -> str` | top | the scratchpad |
| `mem_patch` | `(edit) -> ok` | top | incremental edit; resets each episode |

**Evolvable node = `playbook.md` only** (meta-edited). `notebook` is runtime scratch, not a file.
Worker instructions are authored at runtime by the top (so "how to instruct a worker" is emergent,
not a separate evolvable file).

**Seed (minimal floor — usable mechanism, empty policy):**
- `playbook.md`: ~one line — "Reconstruct a hidden world under a scarce probe budget. You can
  probe, deploy workers with a share of your budget and a task you write, keep an editable
  scratchpad for this world, and submit once. Investigate well; reconstruct as much as you can."
- worker wrapper (fixed boilerplate): "You are a probe worker. Task: {task}. Probe up to {budget},
  then report. Tools: probe, report."
- meta prompt (one paragraph, HyperAgents-minimal): "You improve a research agent. Here is its
  playbook and a sanitized report of how it just investigated several worlds. Make the single most
  impactful, evidence-supported change to the playbook (incl. its memory discipline). Diagnose
  from what happened, not a template. Keep it short." **Do not name "taste"** — that is our word
  for what the lineage discovers, never the agent's target.

Meta-edit discipline: **one coherent, evidence-supported improvement per iteration** (not one
line, not a wholesale rewrite) — for credit assignment and clean ~$1 experiments; selection
already handles safety, so a structural rewrite is fair game when the structure is the bottleneck.

## The world design (the "soul")

**B2, not B1.** The hard part is **allocation** — *which* hypotheses in a too-large space to spend
your next probe/worker on, under deception and shifting goals. The *answer given the data* must be
easy. Avoid **B1** (hard inference / NP reconstruction) — it invites a code solver (trap-tetra) or
breaks the cheap oracle.

**Threshold, restated for the harness era:** the **content** of the winning policy must be
learnable only from play, **not derivable from one world's public structure**. Opus may write the
*method* ("investigate, then exploit") — that is fine — but never the *content*. Build-screen each
family before it ships: **belief-MDP oracle ≫ best articulable heuristic (incl. lookahead)**.

**Battery of virtues** (each a family; the playbook must clear all; the battery *is* the transfer
test of general taste):
- **allocation under scarcity** — the B2 core (budget ≪ space; if you can try everything, no taste
  needed).
- **deception** — locally-attractive ≠ valuable.
- **emergent opportunities** — threads (some traps) surface *as you probe*; taste is which
  serendipitous detour is worth it. Dynamic, non-stationary; subsumes "stepping-stones."
- **variable / expensive-downstream cost** — probes cost different amounts → cost-weighted VoI.
- **calibrated commitment** — when to *stop resolving* and bet on thin evidence; over-investigation
  is punished. ("Knowing what you don't know / when to stop.")

**Knobs that make it cheap *and* tasteful:**
- **small world + tiny budget** → oracle stays computable (simulation) while a punishing
  budget-to-space ratio forces brutal selection. "Too large to try everything" comes from *scarce
  budget*, not a huge world.
- **scarce probes + a wide, growing, *revising* opportunity-map** → pressures the allocator AND
  memory at once. Memory load is the **live decision space** (threads to track, worker reports to
  consolidate, beliefs to revise), not the observation count — which is why scarce budget and
  memory pressure coexist.
- **late disconfirmation** — a thread looks high-value until a late probe reveals a trap. Forces
  tracked **revision** (a flat log can't say "still believed vs. retracted") → pressures *structured*
  memory, and it *is* the falsification virtue. Two birds.

**Why memory structure will emerge (and the condition):** the allocator is pressured *directly* by
coverage; memory is pressured *indirectly*, through the allocator's need for situational awareness
("what do I know / what's ambiguous / what emerged?"), and *only when the episode carries more live
state than fits in head*. So we must **design that density** (above). A flat heap then visibly fails
(re-probing, lost threads, stale beliefs) → coverage drops, the failure is legible in the trajectory
→ the meta agent adds memory discipline to the playbook. Stage it: lean on world-richness pressure
first; add an explicit context/compute budget (MDL on the scratchpad) only if structure still
doesn't emerge.

## The anchor family — concrete draft (next-action 1, DONE)

The B2-allocation core, drafted as a realized, build-screened family: **the trail world**
(`hta/ch2/anchor.py`, screened by `run_anchor.py`, tested by `tests/test_anchor.py`). One
sentence: *follow a trail of pointers through a too-large space to a buried landmark, while fat
"clearing" claims pay you immediately for going the wrong way.* It clears the gate — **belief-MDP
oracle 9.0 vs the best articulable heuristic 6.0, gap 0.50 of the floor→oracle band, the
heuristic landing mid-band (0.50) so a live student has room** — while two controls read 0.00.
The whole point of the reset, made concrete: this gap is pure **allocation** (every cell is a
lookup, never a solve), so it cannot compile into a Python solver and it survives an English
playbook.

**State (the hidden seed).** `R` registers, each an integer in `0..K-1`, uniform — the canonical
anchor is `R=10, K=2` (1024 hypotheses, oracle instant). That is the *entire* hidden state; the
world is a `LinkSpec`-style declarative spec our deterministic expander realizes (safe-eval,
lifted). What the seed fixes that *matters*: where the trail ends.

**Public structure (the rules of the game).** Two register roles, both public; only the values are
hidden:
- **signpost** registers form a public pointer **tree** — `trailhead`'s value picks a `waypoint`
  register, the waypoint's value picks the `landmark` register (a `K×K` fan-out, so *which* register is
  the landmark is genuinely seed-dependent, not readable off the structure). A signpost is read
  through a cheap cell that **pays zero coverage**: it is an instrument (the map's legend), not a
  map cell.
- **clearing** registers each carry a fat **direct block** of `Ld` cells — a big *immediate* coverage
  payoff for one probe. They are the bait, off the trail.
- the **valley** — `Lv` cells mirroring the landmark register — is the deep payoff. It is
  **inference-only**: you *reconstruct* it by walking the trail, you never drill it.

**Probe / cost model.** A probe reads a signpost or a clearing cell and returns its value; the budget
is a **cost** budget (`cost_signpost`, `cost_clearing`), so value-of-information is cost-weighted. The
canonical anchor has budget 3 against ~10 probeable blocks — you cannot try everything. The valley
is not in the probe set; it is scored but never probed.

**The judge / oracle-by-simulation (integrity floor, unchanged).** Coverage = the dumb
deterministic count of cells **logically pinned** by the consistent hypothesis set (every
surviving world agrees). The reference is the **cost-weighted belief-MDP oracle**: the optimal
*adaptive* policy, computed by exact value iteration over belief states — a finite, token-free
belief tree on a world this small. References by verified simulation over the family, never an
LLM. Normalized into a model-free floor→oracle band.

**The build-screen check (reusable gate).** `belief-MDP oracle ≫ best of {greedy-info,
greedy-determined, 2-step lookahead}`, normalized, must clear `MARGIN=0.15`; the ramp must be
anti-cliff. Measured on the canonical anchor: oracle 9.0, best heuristic 6.0 (greedy and the
2-step planner both stall there), **gap 0.50**, ramp max-step 0.22. Two controls confirm the gate
*discriminates*: a world with no valley (`Lv=0`) and one with a slack budget both read **0.00**
(when allocation is trivial there is no gap). And `clairvoyant == oracle` on the anchor — the gap
is the price of the optimal **policy's form**, not of not knowing the world (the same robustness
check the register screen makes). The dials: **`Lv` (the valley-to-clearing mass ratio)** trades gap
against ramp curvature (`Lv` 7→9→12 gives gap 0.25→0.50→0.67), and a **costlier clearing** sharpens
the cost-weighted gap (to 0.71) — the band is narrow, asymmetric, exactly as in `threshold.py`.

**Where the gap comes from (and why it survives the harness).** A bounded planner can climb a
trail whose every step pays `+1`; it cannot climb one whose steps pay **0** with the reward three
probes away. Two structural facts make that hold: signpost reads pay zero coverage, and there are
**at least as many clearing blocks as the budget**, so spending a probe on a zero-coverage signpost
has a strict opportunity cost. The greedy/2-step planner takes the clearings; only the full oracle
commits the three probes to the landmark. And because every cell is a **lookup** (the valley is
`r_landmark + position`, read off once the trail is walked), there is no joint-solve to brute-force —
the B1 trap that let Opus write `trap-tetra`'s oracle is closed. The *method* ("walk the trail,
ignore the clearings") is articulable, and that is fine; the *content* (which register the realized
trail ends on) is in the seed, learnable only by playing **this** instance.

**The five virtues, located honestly.** The model-free gap carries four: **allocation under
scarcity** (budget ≪ blocks), **deception** (clearings pay now, the trail pays only at the end),
**emergent opportunity** (the landmark's identity surfaces only as you walk), and **variable cost**
(the cost knob, demonstrated). The fifth, **calibrated commitment**, is the tiny-budget regime
where the oracle must bet on a partial trail. **Late disconfirmation** turned out *not* to be a
model-free-oracle gap source — it is a **trajectory/memory** pressure (a thread that looks rich
until a late probe retracts it), which is exactly where the design wants it: it shapes the live
student's *revision* and pressures structured memory, so it belongs in the realized world at
calibration time, not in this screen. Each remaining battery virtue is a sibling family with the
same skeleton (swap which signal is deceptive); the battery *is* the transfer test.

## Integrity invariants (survive the reset)
- Objective, agent-inaccessible coverage judge (DP/simulation oracle, never an LLM).
- Safe-eval, lifted: the evolved artifact is text, never executed.
- Airgap via tool confinement; world source never reachable by the player.

## Next actions (staged)
1. **Anchor family** — ✅ **DONE** (see "The anchor family — concrete draft"). The trail world
   (`hta/ch2/anchor.py`, `run_anchor.py`, `tests/test_anchor.py`) is drafted and build-screened:
   state, public structure, probe/cost model, oracle-by-simulation, and the gate (oracle 9.0 ≫
   heuristic 6.0, gap 0.50, controls 0.00). The model-free gap carries allocation/deception/
   emergent/cost; late-disconfirmation is relocated to a live memory pressure (a finding).
2. **Aggressive-staged denoise** — delete the superseded Ch1 numeric pipeline, the closed tape
   slice, the mech-world; collapse the docs to one orientation + archive the slice history as a
   notebook; keep the loop spine (archive, selection, MDL prior, meta-agent, airgap, judge).
   Verify the import graph before each cut.
3. **Reseed** — ✅ **DONE**. The frozen substrate is built and offline-green (45 tests) +
   smoke-validated against the live CLI. `hta/ch2/episode_state.py` is the world-state machine (the
   seven primitives + the band judge: coverage capped to cells the agent's probes pin, normalized
   floor→oracle — ungameable); `hta/ch2/probe_server.py` is the confined stdio-MCP wrapper (top vs.
   worker toolsets = the airgap; `spawn` runs a carve-out worker as a nested `claude -p`);
   `hta/ch2/loop.py` is the model-orchestrated DGM-H loop (the playbook is the Haiku top's
   `--append-system-prompt`; Opus rewrites `seed/playbook.md` only; mock = a deterministic
   floor-player for offline plumbing); `run_loop.py` is the entrypoint. One live episode on the seed
   playbook already reached the oracle's *allocation* (`determined=9`) but left coverage on the
   table at the *submission* (`raw=5`, norm 0.33) — the predicted gradient for the loop.
4. **Wire + calibrate** — ✅ **DONE** (live-validated). Live-eval of the seed surfaced the
   calibration blocker — and it was *legibility*, not just submission wording: `world_map` exposed
   each cell's `reg`/`pos` and the trail tree but **never the value law** (`value = (reg_value + pos)
   mod K`), so although the world is B2 by construction ("reconstruction is a pure lookup") the
   lookup was **unreachable by the agent** — it could only echo the exact cells it probed and
   *guessed* the rest (an invented "alternating pattern"). So it pinned coverage but threw it away
   at submission (`determined=6`, `raw=3`); on most draws it scored **0.00**. The screen's
   heuristics all read the full table — implicitly law-aware, hence 6 — so the live student wasn't
   even on their footing. Two coupled fixes (`hta/ch2/episode_state.py` `world_map` +
   `seed/playbook.md`): **(a)** make the public value law legible in `world_map` (add `value_rule`,
   flag valley cells `mirrors=landmark`) — it is the *same* public structure the oracle/heuristics
   already compute under, so it lifts the live agent onto the screen's footing **without touching the
   band** (gate verdict unchanged: oracle 9.0 ≫ heur 6.0, gap 0.50); **(b)** add reconstruction
   discipline to the seed (submit the forced value for every pinned cell; never guess an un-pinned
   one). **Allocation guidance was deliberately withheld** — walking the trail is the loop's to
   discover. Result, 9 fresh live draws: **mean_norm ≈ 0.50, `raw == determined` on every draw**
   (submission discipline now airtight), bimodal — **6/9 reach the oracle** (Haiku walks
   trailhead→waypoint→landmark and reconstructs the valley) and **3/9 stall at 0.00** (it spends its
   three probes on signposts/the wrong path and pins no coverage cell). That ~⅓ allocation stall is
   the legible, learnable gradient. **Next: run the loop** (Opus rewrites the playbook to cut the
   stall — push the allocation toward the trail) and watch held-out coverage climb off 0.50.

5. **The world-smith (the second loop)** — ✅ **built; model-free proven; the machinery runs and
   extends, validated live.** The agent loop ran (seed → gen_0001, the coach *discovered* "list every
   chain, commit to the deepest", held-out **0.50 → 1.00**), and a stage-1 probe (`run_probe.py`)
   confirmed no *scalar* crank re-opens a gap —
   that note survives every dial, so the gradient lives in the world's **structure**. The world-smith
   (`hta/ch2/world_smith.py`) evolves that structure. Its first move is the **forked trail**
   (`hta/ch2/worlds.py` — `ForkedTrailSpec`/`decoy_spec`): two candidate chains and a **gate** whose
   hidden value selects the live one, so the valley (mirroring the *live* chain's landmark) is pinned
   only by reading the gate **and** walking that chain. Committing to a chain without the cheap gate
   scout pins **zero** valley, whichever chain it is — the structural strategy-trap. The new taste is
   **scout feasibility, then commit** (the fifth battery virtue, calibrated commitment, made structural,
   exactly the "punishes blind full-commitment" the last run pointed at).

   Its **second move** (`worlds.ladder_spec`) proves the family *extends*: the adaptive **gate ladder**.
   The live chain is selected not by one gate but by a *ladder* of gates (read the gate → its hidden
   value names the next gate → … → only the FINAL gate selects the chain), so the whole ladder is
   load-bearing (`gate_chain` ⊆ `trail_regs`) and the decoy's own fix ("scout *the* gate, then commit")
   now reads only the first rung and fails — exactly how `commit_deepest` failed the decoy, one level
   up. The new taste is **scout *adaptively*, then commit**. The inventor proposes only the new
   structure as data (`gate_hops`, a validated field — safe-eval intact); the oracle/coverage re-derive
   mechanically, and the `CURRICULUM` runs the moves in sequence, each coached graduate carrying forward
   as the next move's champion.

   The integrity wall is **lifted, intact**: the inventor proposes only the world's *structure* as
   validated data (`to_dict`/`from_dict`/`validate` — safe-eval lifted, never the score); the referee
   (coverage) and the belief-MDP oracle are **re-derived mechanically** by the *unchanged* `anchor.py`
   machinery (refactored only to dispatch through a small spec protocol — the 46 anchor tests are
   untouched, `episode_state`/`loop` touched minimally so a richer world rides the same airgap). The
   **ship-gate** ships a world only if **hard** (oracle ≫ the generic-planner basket incl. 2-step
   lookahead) ∧ **solvable** (a reachable *method*, `scout_then_commit`, reaches the oracle band) ∧ in
   the **ZPD** (the *champion's* method, `commit_deepest`, *fails* while the new one *succeeds* — the
   only legal coupling is the objective gap on the non-movable scorer, never the agent's internals).

   **Model-free result** (`run_worldsmith.py`, free, deterministic): the decoy **SHIPS** — oracle 11 ≫
   floor 4, gap **0.71n**, anti-cliff ramp, heur **0.29n** (live-student room); "commit to the deepest"
   scores **0.00n** (stalls at the floor), "scout the gate, then commit" scores **1.00n**. The ladder
   **SHIPS** too — oracle 11 ≫ floor 5, gap **0.83n**, heur **0.17n**; "scout the gate, then commit"
   now scores **0.00n** and "scout the ladder, then commit" **1.00n**. A no-fork control (a single
   depth-3 chain, *above* threshold, gap 0.42n) correctly **holds** — the champion already wins it
   (1.00n), so it is not in the ZPD. The SAME method, broken precisely by each structural move.

   **Live result** (`run_worldsmith.py --backend real`, 2026-06-09; 18 `claude -p` calls, **$2.47**): the
   machinery **runs and extends end-to-end** — both moves shipped, the ladder was authored after the
   decoy and slotted into the `CURRICULUM`, the two-iteration two-loop ran live, and each graduate
   carried forward as the next champion, the integrity wall intact one level up. **But the live loop did
   NOT close the gap** (iter 1 decoy 0.00n→0.00n; iter 2 ladder 0.33n→0.00n), and *why* is the finding,
   for the next session's brainstorm:

   - **The model-free gap is not the live student's binding constraint.** The proxies (`commit_deepest`,
     `scout_then_commit`) model an *allocation/scout* failure, but live Haiku **already scouts** (it reads
     the gate, even the ladder, off `world_map`). What it cannot reliably do is the **pointer-chase
     reconstruction** the score actually rewards — follow `head → hop[value] → landmark` and submit the
     valley off the *true* landmark. It mis-resolves the last pointer ~half the time (`determined=9` but
     `raw=0`), an axis the proxies assume away. The world is "hard" on an axis the live student has
     already crossed; it fails on one the proxy is blind to.
   - **Coaching regressed the player.** Opus's edits were strategically excellent — round 2 *diagnosed
     the pointer bug precisely* — but kept a "bank what you can pin for sure" hedge that, against an
     **all-or-nothing valley**, trades the valley for the floor. `coached_1` solved 2/4 ladder worlds;
     the hedge dropped its graduate to 0. Local risk-aversion, global floor-cap.

   The integrity wall did its job: an objective, agent-inaccessible scorer surfaced, honestly, that *the
   proxy we can compute ≠ the constraint that binds the live student*. The two-loop machinery is sound
   and extensible; making the model-free ship-gate **faithful to the live student** (so "champion fails"
   means the *same thing* live) is the precondition for the loop's closure to mean anything — the open
   question carried into the next session.

Cost floor unchanged: a single-session Haiku episode is cents; an Opus meta edit (~$1) dominates a
real iteration. Keep the eval lean.
