# 2026-06-17 — Scaffold the rewrite tree; handoff for wiring LOOP 1

## What this session did

Designed and scaffolded the rewrite tree (the fresh lab), replacing the old skeleton stubs.
The shape is now on disk as docstring-driven stubs — each names its job, its boundary
invariant, and the `_trail/` file to port from. `_trail/`, the `run_*.py` drivers, and the
tests are untouched and green (pytest 67 passed; `run_anchor.py` exit 0).

The cut is four domains, lined up with the rate of change and the integrity floor:

- `lab/` — the grader. **One machine, two uses:** `score_run` (a player's run) and
  `grade_world` (a world's difficulty) ride the same best-play (`oracle`) / lazy-play
  (`floor`) reference points. The "questions every world answers" is a small `World` Protocol
  at the top of `scoring.py`, not its own file. llm-free **by the import graph**.
- `world/` — the content. `spec.py` = the spec format + `validate` + `build` (the safe-eval
  seam: data in, world out, never code). The mutable, family-specific half; also llm-free.
- `dgmh/` — grow the PLAYER (LOOP 1). The play (`play/`), the loop, the meta-edit, and the two
  airgap seams: `report.py` (sanitized conduct → meta-agent, public face only) and `measure.py`
  (selection-blind instruments).
- `gym/` — grow the WORLDS (LOOP 2). Drawn but **docstring-only**; built after LOOP 1 climbs.

Naming settled (jargon retired): `contract`/`screen`/`referee` → folded into `lab/scoring.py`;
`language` → `world/spec.py`; `audit` → `run_logs.py`.

## Invariants now encoded at the seams

- No `hta.llm` import under `lab/` or `world/` — the grader can't be gamed by a model it can't call.
- The airgap is **tool confinement, not an import wall**: the play harness holds the built world
  to answer probes; the player reaches it only through `play/server.py`'s tools. Lintable rule:
  no `oracle|floor|score_run|grade_world` reference under `dgmh/play/`.
- `run_logs.py` is the one radioactive store (transcripts *with* hidden answers) — off every
  agent surface, never a sandbox workspace source, kept out of `archive/`.
- `gym/wish.py` is write-only — new-part proposals flow out to the human, never back to selection.

## NEXT — wire LOOP 1, in this order (each ports from its `_trail/` reference)

1. **`lab/scoring.py`** ← `_trail/anchor.py`: the band math + the exact best-play (`oracle`),
   `floor`, `score_run`. (`grade_world` is LOOP 2 — defer.)
2. **`world/spec.py`** ← `_trail/worlds.py` + author the seed world under `world/seed/`: the
   part types, `validate`, the deterministic `build`.
3. **`dgmh/play/`**: `state.py` ← `_trail/episode_state.py` (state machine + the seven
   primitives); `server.py` ← `_trail/probe_server.py` (the confined MCP surface); `run.py` ←
   `_trail/loop.py::run_episode`.
4. **`dgmh/report.py`** ← the sanitizer in `_trail/loop.py` (the meta-side strip).
5. **`dgmh/loop.py`** ← `_trail/loop.py::run_iteration`; reuse `dgmh/archive.py` and
   `dgmh/sandbox.py` as-is; `meta.py` ← `_trail/loop.py::meta_edit`.
6. **`dgmh/measure.py`**: start with the held-out climb; the **port check** (playbook on a
   weaker model) is the load-bearing one for the transfer thesis.
7. Repoint `run_loop.py` from `hta._trail.loop` to `hta.dgmh.loop`; add tests; only then is
   `_trail/` deletable.

## Gotchas (from CLAUDE.md, easy to forget)

- **Probes (cost) bind, not turns** — budget a play by probes; give turns generous headroom.
- **One agent session per play**, not one call per probe — the ~31k-token system-prompt tax
  makes call *count* the cost driver. Use a staged-eval gate before multiplying eval repeats.
- Order of magnitude: a Haiku play is cents; an Opus meta-edit is ~$1 and dominates a real iteration.

## Deferred (don't build speculatively)

- All of `gym/` (LOOP 2) — until LOOP 1 climbs.
- Lift `dgmh/archive.py` → shared `hta/archive/` — when `_trail/` retires (both loops then import it).
- Centralize the calibration thresholds into `config.py` — when LOOP 1 code first needs them.
