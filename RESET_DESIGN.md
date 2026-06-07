# Chapter-2 reset — the design we locked (decision record)

This is the forward design from the session that followed the "harness writes the oracle"
finding (`WORLD_DESIGN.md` → "The harness substrate"). It supersedes the Chapter-2 *mechanics*
in `WORLD_DESIGN.md`; the slice-by-slice history there is now lab-notebook, to be archived in the
denoise. Read this first.

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
   (buffered, slotted, …) is for the loop to invent, like the allocator.

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

## Integrity invariants (survive the reset)
- Objective, agent-inaccessible coverage judge (DP/simulation oracle, never an LLM).
- Safe-eval, lifted: the evolved artifact is text, never executed.
- Airgap via tool confinement; world source never reachable by the player.

## Next actions (staged)
1. **Anchor family** — draft the concrete B2-allocation core carrying deception + variable cost +
   emergent opportunities + late disconfirmation under tiny budget: state, public structure, the
   probe/cost model, the oracle-by-simulation, the build-screen check. The other four virtues are
   variations on it.
2. **Aggressive-staged denoise** — delete the superseded Ch1 numeric pipeline, the closed tape
   slice, the mech-world; collapse the docs to one orientation + archive the slice history as a
   notebook; keep the loop spine (archive, selection, MDL prior, meta-agent, airgap, judge).
   Verify the import graph before each cut.
3. **Reseed** — frozen primitive harness, model-orchestrated (B), confined tools, editable
   scratchpad, empty playbook, one-paragraph meta.
4. **Wire + calibrate** — loop on the anchor family; calibrate live so Haiku lands in-band; run.

Cost floor unchanged: a single-session Haiku episode is cents; an Opus meta edit (~$1) dominates a
real iteration. Keep the eval lean.
