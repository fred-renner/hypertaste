# 2026-06-17 — The first real world landed (the `prospect` family + seed)

Continues `findings/2026-06-17-grader-landed-handoff.md`. The grader was already on `main`; this
session built the *world* it grades. LOOP-1's play spine and all of `gym/` are still deferred — the
binding constraint was a world worth climbing, not the player loop.

## What landed

- `hta/world/spec.py` — the **`prospect`** spec family: the part box, `validate` (the safe-eval
  wall: data in, raises on an illegal wiring), and the deterministic `build` (spec → a `World` the
  grader reads; the hidden answer drawn from `seed`, held harness-side, never on a player surface).
- `hta/world/seed/prospect.py` — the authored **seed world**, one real parts-list in the language
  (the smith's worked example, DESIGN §7), plus `build_seed(seed)`.
- `tests/test_world_spec.py` — 16 tests: validate rejects every illegal wiring; build is
  deterministic and model-free; the band is certified; and the gap is shown to be *taste*.
- Full suite **90 passed** (was 74); `run_anchor.py` exit 0. `_trail/` untouched.

## The world — three parts, one move

`R=10` hidden registers (K=2 → 1024 hypotheses, small so the exact oracle stays computable). Three
kinds of part, and the floor→oracle gap is the same tasteful move read three ways:

- **clearing** (regs 0,1) — immediate-payoff **bait**: scored cells you can also probe. A lazy
  player grabs them (they set the floor); a greedy player over-invests and never starts the deep
  work. The deception.
- **vein** (pointer reg 2 → ore pool {3,4}) — a depth-2 **inference** seam. *Which* ore is live is
  the hidden pointer value, **fresh every episode**, so there is no memorisable answer: you read the
  position to pick the probe. Pays nothing until pointer *and* ore both land.
- **prospect** (assay reg 5 → pointer reg 6 → ore {7,8}, noise reg 9) — a graded, depth-3 seam, the
  richest payoff (8 cells) but **barren half the time**. A barren vein mirrors the **unprobeable**
  noise register, so it can *never* be pinned — a real **dead end**. The tasteful move is to assay
  first and **turn around** on a barren vein instead of sinking the deepest shaft into it (the
  learning-gradient / boredom habit, DESIGN §2 — the thing both the trail and instance-0 lacked).

Budget 5 is tight: you cannot do everything, so allocation under scarcity binds.

## Why the gap is taste, not a tactic (certified mechanically)

The cut from the trail: the value law (rich→live-ore, barren→noise) lives entirely in the world's
`observe`, **never in the grader** — that tangle was the trail's tell, and keeping it out is what
makes the grader generic. The seed world's separation, all measured by the grader's own engine:

| play | score | reads as |
|------|-------|----------|
| `floor` (lazy)            | 4  | grab the bait only |
| greedy (1-step, myopic)   | 4  | never starts a seam (every first probe pays 0 coverage) |
| lookahead-2 (bounded)     | 8  | mines the shallow **vein**, misses the deep prospect |
| lookahead-3 ≈ `oracle`    | 10 | assay-triage + depth-3 commitment + position-reading |

`grade_world`: **gap 6, reachable 0.625, hard ✓ solvable ✓.** The world demands depth-3 adaptive
play with dead-end triage — a myopic reflex earns only the bait, a 2-step formula stalls at the
shallow vein. That `oracle > lookahead-2 > greedy` ladder is the anti-tactic guarantee, pinned in a
test. (Endpoints 4/10 are hand-checked too.)

## Honest caveats (don't oversell — instance-0 lesson #3)

- **The depth is 3 by construction**, so a depth-3 planner *matches* the oracle. That is deliberate
  (keep the oracle computable) and meets the trail's own bar (beat the *bounded* depth-2 planner) —
  but it means "no cheap formula" holds against *shallow* planning, not against arbitrarily deep
  search. The richer hardness check (oracle must beat a greedy/bounded planner) is still **deferred
  in `grade_world`**; here it is shown only for the seed, in a throwaway test baseline.
- **This is read off the band and the planners, not off a grown playbook.** The real proof — read
  taste off the evolved playbook in plain English (position → move, portable) on the live loop — is
  still owed, and needs LOOP-1's play spine (next).
- One vein + one prospect is a modest instance; richer triage (more seams) is a knob the smith will
  later turn. The language already expresses it; the seed stays small for a fast, computable oracle.

## NEXT (unchanged order, now unblocked)

`dgmh/play/` — the confined MCP surface + state machine + `run_episode` — against this world
(`findings/2026-06-17-scaffold-rewrite-tree.md` step 3 onward). The world to climb now exists.
