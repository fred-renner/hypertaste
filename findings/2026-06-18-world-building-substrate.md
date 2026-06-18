# Handoff — the principled world-building substrate (offline, model-free)

*Lab note, 2026-06-18. The build spec for the next instance. Builds on the engine note
(`findings/2026-06-18-world-engine-design.md`), which introduced the dumb-player battery and the
ZPD screen; this note pins down the grammar slice, the seed, and the offline proof so a fresh
session can execute without re-deriving the design.*

## Context

World-building has failed three times by **constructing** a world and burying it in a story, which
re-anchors the next session. LOOP 1 has been turned several times; it led nowhere because the
*substrate* under it was wrong — a green end-to-end run on bad infra proved nothing. The repo shows
the trap directly: `hta/_trail/worlds.py` + `world_smith.py` are a **complete, working** world-smith
(spec → validator → expander → model-free ship-gate with a champion-fails/fix-succeeds check → live
coaching demo) — but every noun is the trail story (chains, signposts, valleys, gates). Generalizing
*from* it welds the project to "forked chains." That is the lock-in we are refusing.

So we build the world-building **machinery from first principles**, derived from the rules, not from
a world — and prove it **offline, model-free, against the already-frozen grader** before any live
loop. Decision (this session): **scope = smith substrate, offline; grammar slice = minimal (variables
+ gated readouts).** The LLM inventor, LOOP 1, the taste-check, and full LOOP 2 are explicitly later.

**Forcing function — the seed is the grammar's unit test, not a showcase.** A grammar invented purely
in the abstract fails two ways: **too weak** (every world it can express is solved by grabbing the
nearest payoff → no look-ahead is ever required → no taste in anything it builds) or **too loose** (it
lets you write a world the dumb scorer can't grade — ill-posed readout, unbounded hypotheses, a payoff
that's never pinnable). So we author **one seed inside the grammar that pushes the exact property we
care about** — *can this vocabulary express a world that genuinely forces allocation under scarcity and
still be graded mechanically?* — and run it (plus mechanical variants) through the frozen grader + the
dumb-player battery. If no such seed can be authored, the grammar is too weak — fix the **grammar**, not
the world. If authoring one surfaces a build-but-can't-grade world, the grammar is too loose. If the
seed comes out hard + solvable with `validate`/`build` total, the grammar survived. This is
falsification — the discipline that stops "principled" from becoming "untested." The world is the
**test** of the grammar, never its **source**.

## What's already done — do not rebuild

- **The grader** (`hta/lab/scoring.py`, frozen): `oracle / floor / score_run / grade_world` ride any
  `World` (a thing answering `hypotheses / positions / cost / observe / probeable / scored`); the
  oracle is an exact belief-MDP, lru-cached on the tableau. **Do not touch it.**
- **Config gates** (`hta/config.py`): `world_gap_min=1.0`, `world_reach_min=0.5`.
- **The sandbox airgap** (`hta/dgmh/sandbox.py`) and **archive** (`hta/dgmh/archive.py`) — genome-
  agnostic, but the archive is keyed to program *directories*; wiring worlds into it is full-LOOP-2,
  not this pass.
- The trail (`hta/_trail/`) — a **mechanics reference only** (how a tableau / a gate / a model-free
  champion-vs-fix screen are computed). Its *vocabulary* is discarded.

## The grammar — variables + gated readouts (first principles)

Derive the part vocabulary from what the four guardrails *force* against the grader's five questions,
**not** from chains. Authored in `hta/world/spec.py` (fill the `validate`/`build` stubs):

- **Variables** — the hidden unknowns. A spec lists `n_vars` variables, each over `K` values →
  `hypotheses()` is their product (kept enumerable, e.g. ~8 vars × K=2, like the trail's scale).
- **Readouts** — the positions. Each readout's `observe(pos, hyp)` is a fixed deterministic function
  of a subset of variables (a lookup, never a solve). Three roles, all expressed in this one kit:
  - **immediate readout** (scored): reveals one variable directly → pays coverage now = greedy bait.
  - **gate readout** (cheap, *unscored*): reveals a prerequisite variable; pays zero coverage = pure
    feasibility pointer.
  - **gated payoff** (scored): its value depends on a prerequisite set of variables and is **constant
    across all hypotheses until that set is jointly pinned** — the chain trick, stated as *a readout
    over a prerequisite set*, so it is "earned" only by scouting the gate(s) first. Committing budget
    without the scout pins nothing.
- **Costs + budget** = scarcity; **scored-set** = which readouts count. "Chains" are then just *one*
  composition of gates, not a primitive — deeper earned access = a longer prerequisite path
  (compounding horizon) with no new part type.
- **Safe-eval**: the spec is data with `to_dict`/`from_dict`; `validate` rejects illegal wiring
  (out-of-range variable refs, empty scored-set, no bait, budget < 1, a gated payoff with no gate);
  `build` is a deterministic expander, data in → `World` out, never executed.

**Relabeling is out of scope here** (no live play) but `build` must stay structure-only so a per-
episode relabel can sit *above* `World` later (a play-surface concern, never in `build`).

## The seed (inside the existing `hta/world/seed/` package — e.g. `hta/world/seed/__init__.py`)

> Note: `hta/world/seed/` already exists as a directory (currently a `.gitkeep` placeholder). Author the
> seed as a module *inside* it (exposing `seed_spec()`), not a colliding top-level `hta/world/seed.py`.

The **smallest world that genuinely demands multi-horizon allocation under scarcity** — not "3 boxes,
be tasteful in 3 probes." Authored *in the grammar*: a few immediate readouts (bait), one gate
variable read via a cheap gate readout, and a gated payoff worth more coverage than the bait but
pinnable only via gate→target, under a budget that fits *scout-the-gate + read-the-target + light
mop-up* but **not** *grab all the bait*. Exact numbers are **calibrated against `grade_world` + the
battery** (hard + solvable + ZPD-capable structure, see below), the way the trail's decoy was tuned
(floor 4 → oracle 11) — not hand-fixed up front.

## The dumb-player battery + ship-gate (`hta/gym/`)

- **`hta/gym/battery.py` (new)** — a thin **model-free** policy simulator over the `World` interface:
  for a scripted `pick` policy, play it against each hypothesis-as-truth (track belief via
  `world.observe`, submit the pinned scored readouts), and place each playout with the frozen
  `score_run`; average. Members: **greedy** (grab biggest immediate coverage), **random**, **sweep**,
  **shallow look-ahead**. Plus two **ZPD stand-in policies** over the generic grammar: a *champion*
  analogue (greedy, ignores gates) and a *fix* (pin the gate variable first, then read the gated
  payoff). It is a **gate/diagnostic, never a number the smith grows** (guarded by comment + by not
  exposing it to the smith).
- **`hta/gym/ship_gate.py`** (fill stub) — realize the spec via `build`, then verdict =
  - **hard**: `grade_world` says hard **and** `oracle` beats the best battery member by
    `world_battery_margin` (the stronger bar the engine note calls for);
  - **solvable**: `grade_world` says solvable **and** the fix policy reaches the band;
  - **ZPD-capable structure**: the champion stand-in stalls (≤ fail bar) while the fix succeeds — a
    *necessary screen*, not a measurement of true ZPD (see the boundary note below).
  `ship = valid & hard & solvable & zpd_capable`. Re-derived mechanically; the smith never asserts it.
- **`hta/gym/smith.py`** (fill stub) — **deterministic mutation operators on the spec** (add/remove a
  bait readout, add/retarget a gate layer = deepen earned access, scale budget/costs). **Not** the LLM
  inventor — these exist only to produce a spread of variant specs that exercise the ship-gate.
- **`hta/gym/loop.py`** (light) — a thin offline driver: seed → mutate → ship-gate → collect verdicts.
  No archive, no LLM. `hta/gym/wish.py` stays a stub (human-gate / full-LOOP-2 concern).

### What "ZPD" means offline — the honest boundary

True ZPD is defined **against a specific agent** (hard for *it*, reachable with one more move). There is
no agent in this pass, so we do **not** measure true ZPD and must not claim to. The battery's scripted
policies are *articulated strategies*, not the model: greedy/sweep stand in for "grab the nearest
payoff," scout-then-read for "earn the gated payoff first." They **bracket** the world — greedy is a
floor on the naive move, scout-then-read a witness that a skilled move reaches the band — so the gap
between them is **room for taste**, a property of the world's geometry, agent-independent and free to
compute. It is a **necessary condition**: no gap (greedy already ≈ oracle) → definitely no ZPD, reject
cheaply; gap present → the world *can* host a ZPD. Whether the **live champion** actually sits in that
gap is what LOOP 1 measures later, with a real agent. (The trail's ship-gate already screens this way,
deliberately, to stay deterministic and free.)

## Config (`hta/config.py`)

Add, surfaced not hardcoded, next to `world_gap_min`/`world_reach_min`: `world_battery_margin` (how
far `oracle` must beat the best scripted player) and the ZPD `world_zpd_fail_bar` /
`world_zpd_solve_bar`. **Starting defaults = the trail's known-good hardcodes** (`_trail/world_smith.py`:
`MARGIN=0.15`, `FAIL_BAR=0.30`, `SOLVE_BAR=0.85`) — lifted out of the code into config, then re-calibrated
against the seed, not re-guessed.

## Explicitly deferred (later passes, not now)

LLM inventor in `smith.py`; the compass (learning-progress × transfer); archive-of-worlds wiring; the
wish channel; LOOP 1's play/server + live champion + taste-read; instrument-building (a deliberate,
human-gated grader tier-up).

## Verification (offline, free, deterministic)

`tests/` (mirroring the existing layout):
- `tests/test_world_spec.py` — `validate` rejects illegal specs; `build` yields a `World` the grader
  rides; the seed's `oracle > floor` and `grade_world` reports `hard` + `solvable`.
- `tests/test_battery.py` — on the seed, `oracle` clears the best scripted member by the margin; a
  **flat / gate-removed** variant is rejected (greedy ≈ oracle → nothing to learn).
- `tests/test_ship_gate.py` — seed **ships** (champion stalls, fix succeeds); the mutation spread
  produces the *expected* admit/reject (remove gate → reject trivial; over-tighten budget → reject
  unsolvable; deepen gate → still ships, harder).
- `tests/test_integrity.py` — no `hta.llm` import reachable under `hta/lab/` or `hta/world/`; the
  smith emits only specs (no score field).
- Run: `pip install pytest && python -m pytest tests/ -q`, plus `python run_anchor.py` stays green
  (trail untouched). Optional thin driver `run_smith.py` to watch seed→mutate→gate offline.

## Definition of done

The grammar expands to valid graded worlds; the seed is **certified hard + solvable + ZPD-capable
structure** (per the boundary note — scripted-player screen, not true ZPD) by the frozen grader and the
battery, fully offline; the mutation machinery exercises the ship-gate across a correct admit/reject
spread. The substrate is proven before any live loop touches it — then hand off to LOOP 1, which is
where true ZPD (against a live champion) and the LLM inventor enter.
