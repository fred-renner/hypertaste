# CLAUDE.md

Guidance for Claude Code working in this repository.

## Orientation

`hypertaste` is a self-improving research-taste harness (DGM-H pipeline): it co-evolves a task
agent and its curriculum so the agent grows **taste** — *choosing your next move well by
evaluating your position*. (The thesis: taste is the situational trigger, not the capability —
the moves are the model's; which one fires from the position read is the grown procedure, so it
should port onto even a weak model.)

- **The design — read first:** `DESIGN.md` (the current taste definition, the rules any world
  must meet, and the machinery).
- Vision: `ROADMAP.md` → "The gym and its chains".
- How to run the current code (the anchor reference chapter): `README.md`.
- Last lab note: `findings/2026-06-14-instance0-machine-world.md` (instance 0 read as a tactic,
  not taste — the why behind this cleanup).
- History — kept, not current: everything under `history/` (`RESET_DESIGN.md` the anchor-trail
  chapter, `PLAN.md` / `REPLAN.md` / `NEXT.md` the superseded plans, `NOTEBOOK.md` the lab log).

This file plus `README.md` are the orientation — open only the files you're about to change
rather than re-reading the whole tree.

## Voice & altitude — working with the PI

The user is the PI: fluent in the framework's *concepts and architecture* (research taste,
the ZPD, the two-loop model, the staircase of judges, transfer, the integrity floor) but
**not** its implementation details. Open in that register, especially on direction/strategy
questions — match the depth and tone of a genuine research-design conversation.

- **Read which mode they're in.** *Design/strategy* (thinking about direction — the
  default for open questions): lead with the concept, reason through the long-horizon
  thesis, use a sharp analogy, name the relevant pattern (learning-progress curricula,
  reward-hacking/Goodhart, warm-start vs. reset) when it clarifies — and keep code/`file:line`
  refs **out** unless asked. *Implementation* (changing the system): the verdict-first,
  `file:line` style under "Token efficiency → Answers".
- **Explain at concept altitude.** Don't assume code knowledge; don't bury the point in
  internals. When they say "leave out the details," give the idea, not the mechanism.
- **Plain-language rule (PI sessions).** Every technical term gets one plain sentence the
  first time it appears, or it doesn't appear. One idea per sentence. Prefer a concrete
  example to an abstract noun. Never stack freshly coined compound terms ("by-construction
  local-identifiability certificate") — say what the thing does instead. Test before
  sending: would this paragraph survive being read aloud to a smart colleague from another
  field? The PI's concept vocabulary (ZPD, Goodhart, the null, taste, transfer) is fine;
  invented shorthand is not.
- **Engage, don't deflect.** Take the hard design questions seriously (closing the loop,
  seeding, the steepest gradient, ZPD); push back with crisp distinctions and honest
  boundaries (e.g. "99% hands-off is the prize; 100% is wireheading") rather than hedging.
- **Always recommend, never offload** the decision; back the call with reasoning, caveats
  short and last.

## Run & test

**Where we are (2026-06-16):** the repo was re-cut around the system's loops (see `DESIGN.md`).
Shared plumbing sits at the top (`hta/llm.py`, `hta/config.py`); `hta/dgmh/` is LOOP 1 (grow the
agent — the archive, the program-length prior, the meta-agent airgap), `hta/gym/` is LOOP 2 (grow
the world — the world-smith), and `hta/world/` is the agent-inaccessible world. The retired trail
puzzle is **quarantined** in `hta/_trail/` as a temporary test world — it still runs and backs the
tests. The fresh lab inside `world/`, `dgmh/episode/`, `dgmh/loop.py`, and `gym/` is **skeleton-
stubbed**, built in the next pass against the contract designed from `DESIGN.md`.

```bash
python run_anchor.py                              # anchor build gate: free, model-free, deterministic
pip install pytest && python -m pytest tests/ -q  # tests (pytest is not preinstalled)
python run_loop.py --iterations 1 --backend mock  # the loop, offline (deterministic floor-player)
python run_loop.py --iterations 1 --backend real  # the loop, live (cents/Haiku episode, ~$1/Opus edit)
python run_probe.py --backend real                # stage-1: champion vs a scalar-harder world (cents)
python run_worldsmith.py                          # ship-gate both curriculum moves: free, model-free (slow)
python run_worldsmith.py --backend real           # + the LIVE two-iteration two-loop (~$2.5 total)
```

The `claude` CLI is installed and authenticated here, so the `real` backend works without an API
key (subscription auth). The runtime is stdlib-only (Python 3.11); `pytest` is the only dev
dependency.

## Files you'll edit vs. leave alone

**Shared plumbing + the machinery — keep, it's world-agnostic and reusable:** `hta/llm.py` (the
`claude -p` seam — `complete` / `episode` / `agentic` adapters + mock + accounting) and
`hta/config.py` (knobs) at the top; `hta/dgmh/archive.py` (archive + open-ended selection, with the
program-length prior folded in) and `hta/dgmh/sandbox.py` (the meta-agent airgap: Direct | Docker).
This is what survives every chapter.

**The quarantined trail — a frozen reference fixture in `hta/_trail/`** (leave alone unless
deliberately reworking it; design write-up `history/RESET_DESIGN.md`): `anchor.py` (the trail world
+ oracle + build-screen, generic over a spec protocol), `worlds.py` (the world-smith's structural
family), `world_smith.py` (the second loop — ship-gate + inventor scaffold + curriculum demo),
`episode_state.py` (world-state machine + band judge), `probe_server.py` (confined stdio-MCP + the
seven primitives), `loop.py` (the model-orchestrated DGM-H loop + the Opus `meta_edit`), and
`seed/playbook.md` + `champion/playbook.md`. The `run_*.py` drivers still point here. It is the one
worked example; it is deleted once the fresh lab carries its own tests.

**The fresh lab — skeleton-stubbed, built in the next pass:** `hta/world/` (the contract + the dumb
scorer/band), `hta/dgmh/episode/` (the play + the airgap), `hta/dgmh/loop.py`, and `hta/gym/` (the
world-smith). Built from `DESIGN.md`'s principles — reusing the machinery and the trail as the
worked example, not re-cloning the loop.

## The two invariants (the integrity floor — they survive every chapter)

- **Objective, agent-inaccessible scoring** — worlds are scored by a **dumb deterministic
  function**, never an LLM judge (the agent is optimized *against* the score, so a movable
  score is reward-hacking). *The trail:* information-weighted **coverage** = cells logically pinned by
  the consistent hypothesis set, normalized into a model-free **floor→oracle band**; the oracle
  is the exact adaptive belief-MDP policy, **by simulation** over the world family
  (`hta/_trail/anchor.py`). The world stays **deterministic** so the oracle is computable.
  *Lifted to the second loop (the world-smith):* the same wall holds one level up — **the inventor
  proposes only the world's *structure*, never the score.** The referee (coverage) and the
  perfect-play benchmark (oracle) are **re-derived mechanically** from that structure, and a world
  ships only if it is still **hard** (oracle ≫ greedy) **and solvable** within budget. An inventor
  that could also move the score would just mint worlds that *look* solved — the exact trap that
  forced the reset.
- **Safe-eval, lifted** — model output never executes. *The trail:* the evolved artifact is **text**
  (`playbook.md`), read by the harness as context only — never imported or run. (Worlds are
  realized from a **validated declarative spec** by a deterministic expander — same principle.)

## Gotchas

- **Probes (cost), not turns, bind** — budget an episode by the probe/cost budget; give turns
  generous headroom so the scarce resource is the probe.
- **The airgap is tool confinement.** Probing always goes through a confined agent/tool; free
  Python may only compute over what was *probed*, never read the world source. Hierarchy is the
  harness spawning probe-only worker sessions — not claude's general `Task` tool.
- `--sandbox none` is the soft airgap (Bash denied, in-process); `--sandbox docker` is the hard
  one (slower, same token cost) — it runs the meta agent in a container with no repo or world
  source, mounting `~/.claude` read-only so it auths on the host subscription.
- A non-solving agent that spends all its probes is a legitimate worst-score failure — worlds are
  gated to be solvable within budget, so we don't rescue it.

## Token efficiency

Token efficiency matters at every level:

- **The harness:** every `claude -p` call carries a fixed ~31k-token system-prompt tax, so
  minimize call *count* (one agent session per episode, not one call per probe), keep prompts and
  the eval report lean, and don't multiply cost (e.g. eval repeats) without a staged-eval gate to
  cap it.
- **The code:** prefer the smallest design that meets the need; delete dead paths and stale
  docs rather than letting them accrue.
- **Working style:** be concise, parallelize independent tool calls, don't re-read files,
  don't pad explanations.
- **Answers (implementation mode; for design/strategy see "Voice & altitude"):** lead with
  the verdict (do/skip + the action), back claims with `file:line`, recommend rather than
  offload the decision, keep caveats short and last, and don't frontload detail that wasn't
  asked for — expand on request.

Order of magnitude: a Haiku task call/episode is a few cents; an Opus meta-agent edit is
~$1 and dominates the cost of a real iteration. Call out the token/cost impact of changes.

## Finalizing — land on `main`

Done = merged to `main` and pushed, not a dangling feature branch. As the final step, with
standing permission (no confirmation): green `pytest` (skip for docs-only) → **`git fetch origin`
first** → merge the working branch (fast-forward when possible) → `git push origin main`.

> **Gotcha (why "land on main" keeps jamming):** the container can boot with a **stale
> `origin/main`** — it points at a *superseded, unrelated-history* line (the pre-reset
> "first commit" / world-design era) from before `main` was reset to the current line. Until you
> `git fetch`, `main` looks like an unrelated history that can't merge, when in fact your branch is
> a clean fast-forward of the *real* `main`. Always fetch before reasoning about `main`; never
> force-replace it on the strength of the stale local ref.
