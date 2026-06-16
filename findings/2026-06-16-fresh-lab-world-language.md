# Finding — the fresh lab: the world language + the two loops, built (2026-06-16)

The "next pass" after the re-cut (the skeleton-stubbed `hta/world/`, `hta/dgmh/episode/`,
`hta/dgmh/loop.py`, `hta/gym/`). What got built, the one design call it turned on, and what is and
is not yet shown. A lab note, not a current design — `DESIGN.md` remains the design.

## What we set out to do

Fill the four stubs against `DESIGN.md`: build **the world *language*** (§5 — a part-box plus
wiring, not a fixed world), authored an **instance 0** as a real parts-list in it (§7), and run it
through **one world-agnostic loop** — the post-mortem's prescription for the instance-0 miss
(findings/2026-06-14 §3: "fold into one world-agnostic loop", run the real meta + task loop).
Reuse the trail's proven machinery; do not re-clone the welded loop.

## The one design call (the open §9.2 — how much language to build first)

The smallest slice that (a) subsumes the whole trail family as instances and (b) lets instance 0 be
a *position worth reading*. A **part-box** — `Clearing` (a variable paying coverage immediately),
`Chain` (a pointer trail of cheap signposts to a hidden landmark), `Fork` (a gate ladder selecting
which chain is live, driving a deep valley) — composed into a **`WorldSpec` = a list of regions over
a shared variable pool**. This is strictly more expressive than the monolithic `ForkedTrailSpec`
(several forks + standalone clearings compose; the per-region valley resolution is the generalization
that makes it a grammar, not a world), yet it collapses the anchor / decoy / ladder into single-fork
instances — so the trail's *validated* numbers carry over exactly.

## What got built

- `hta/world/` — the world LANGUAGE: `language.py` (the part-box + `WorldSpec` + `validate` + the
  deterministic expander), `grade.py` (the world-agnostic grading engine — the dumb coverage scorer,
  the no-inference floor, the belief-MDP oracle, the build-screen), `contract.py` (the documented
  `World` interface + the band/score/realize facade), `instances.py` (instance 0 + named worlds as
  parts-lists).
- `hta/dgmh/episode/` — the play + the airgap: `state.py` (the world-state machine + the band judge,
  generic over a `WorldSpec`) and `server.py` (the stdio-MCP probe server).
- `hta/dgmh/loop.py` — the world-agnostic DGM-H loop: the world is just a `WorldSpec` argument;
  reuses the archive + open-ended selection + the Opus self-modify airgap wholesale.
- `hta/gym/smith.py` — the world-smith: the ship-gate (hard ∧ solvable ∧ the ZPD), the model-free
  champion/fix instruments, the safe-eval inventor realizer, the curriculum + closed-loop demo.
- `run_lab.py` (screen / loop / smith) and a full offline test suite (33 fresh tests; 100 total).

## What the model-free screen says (the integrity floor, re-derived mechanically)

| world | hyps | floor → oracle | gap | reads |
|---|---|---|---|---|
| single-chain (control) | 512 | 3 → 9 | 0.42n | above threshold; no fork to scout |
| **instance0** (the worked world) | 1024 | 4 → 11 | **0.71n** | above threshold, anti-cliff, heur 0.29n |
| ladder (the smith's harder move) | 4096 | 5 → 11 | 0.83n | above threshold; lookahead-2 stalls at 6 |

The ship-gate's ZPD coupling holds both moves: on instance0 the depth-committing rule stalls at the
floor (0.00n) while scout-then-commit reaches the ceiling (1.00n); one level up, scout-the-gate
becomes the failing champion and scout-the-ladder the fix — the outer loop closing on itself. All
re-derived by the unchanged grading math from the structure alone; the smith proposes only structure.

## The honest reading

- **It is the lab, end to end, world-agnostic.** The mock loop runs a full DGM-H iteration on
  instance 0 (seed → eval → branch → eval → archive), the judge is a pure replay, the airgap and the
  role confinement are unit-tested offline. This is the scaffolding the post-mortem asked for: one
  loop, not a bespoke driver welded to a world.
- **The two invariants held.** Objective agent-inaccessible scoring (a dumb `f(structure,
  observations)`, never an LLM judge), and safe-eval lifted (the evolved unit is the English
  playbook; worlds are realized from a validated declarative parts-list, never executed).
- **instance 0 is a position worth reading**, not the retired flat allocation world: connected chains
  (depth), a valley that pays only end-to-end (compounding access), a wrong chain that pins nothing
  (a dead end), cheap gate/signpost reads (instruments). The tasteful move it plants — scout which
  chain is live before committing — is a facet of the §1 principle, never scripted for the player.
- **Not yet shown: the live result.** Everything here is model-free or mock. The bar — taste readable
  off a grown playbook as *position → move*, portable, on the real Haiku + Opus loop — is exactly what
  `run_lab.py loop --backend real` and `smith --backend real` are for, and has not been run here.

## For next time (pointers, not a plan)

- Run `run_lab.py loop --backend real` to calibrate Haiku into the band on instance 0, then read the
  grown playbook for the scout-then-commit habit *in its own words*.
- The trail (`hta/_trail`) is now redundant: the fresh lab carries its own tests and worked example.
  It can be deleted in a follow-up once the live loop has been exercised once on the fresh lab.
- Compose the language: a two-fork world (two structured regions, the budget split across them) is the
  next structural move the smith can author without a new part type.
