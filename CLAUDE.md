# CLAUDE.md

Guidance for Claude Code working in this repository.

## Orientation

`hypertaste` is a self-improving research-taste harness (DGM-H pipeline): it co-evolves a
task agent and its curriculum on a "discover the hidden structure by probing" world.

- Architecture + how to run the **current code** (Chapter 2, post-reset): `README.md`.
- Long-term direction (the two-loop model, staircase of judges, closing the loop): `ROADMAP.md`.
- Design + rationale for the **current chapter** (Chapter 2 after the reset — the English
  playbook, the model-orchestrated harness, the anchor trail world): `RESET_DESIGN.md`.
- Archived Chapter-2 lab history (the tape slices, the trap-tetra "harness writes the oracle"
  finding that triggered the reset): `NOTEBOOK.md`.

This file plus `README.md` are the orientation — open only the files you're about to
change rather than re-reading the whole tree. `ROADMAP.md` is the direction; `RESET_DESIGN.md`
is the current chapter's mechanics; `NOTEBOOK.md` is history.

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
- **Engage, don't deflect.** Take the hard design questions seriously (closing the loop,
  seeding, the steepest gradient, ZPD); push back with crisp distinctions and honest
  boundaries (e.g. "99% hands-off is the prize; 100% is wireheading") rather than hedging.
- **Always recommend, never offload** the decision; back the call with reasoning, caveats
  short and last.

## Run & test

**Where we are:** the Chapter-2 **reset** is locked (`RESET_DESIGN.md`), the **denoise is done**, and
the **reseed is built** — the repo is the loop spine (archive, MDL prior, meta-agent, sandbox airgap,
llm, config), the **anchor trail world** (`hta/ch2/anchor.py`, build-screened by `run_anchor.py`),
and the **option-B substrate**: `hta/ch2/episode_state.py` (world-state machine + band judge),
`hta/ch2/probe_server.py` (confined stdio-MCP, the seven primitives + `spawn`), `hta/ch2/loop.py`
(the model-orchestrated DGM-H loop), `hta/ch2/seed/playbook.md` (the only evolvable node), and
`run_loop.py`. Offline-green (46 tests), and **calibrated live**: the seed now lands **mean_norm ≈
0.50 in-band** (see below).

**Next action — RUN THE LOOP** (`RESET_DESIGN.md` → "Next actions" 4 is now ✅ DONE):

The calibrate step is landed. Live-eval surfaced the blocker as *legibility*: `world_map` hid the
public value law (`value = (reg_value + pos) mod K`), so the B2 "reconstruction is a lookup" was
unreachable — the agent pinned coverage (`determined=6`) but *guessed* the submission (`raw=3`),
scoring ~0. Fix (committed): make the law legible in `world_map` (`value_rule` + valley
`mirrors=landmark`) **without touching the band** (gate still oracle 9.0 ≫ heur 6.0), plus
reconstruction discipline in the seed (submit every pinned cell, never guess). Now, 9 fresh live
draws: **`raw == determined` on every draw** (submission airtight) and **mean_norm ≈ 0.50**, bimodal
— **~6/9 walk the trail to the oracle**, **~3/9 stall** on signposts. **Allocation was withheld from
the seed on purpose** — that ~⅓ stall is the gradient.

So the next dial is the **loop itself**: `python run_loop.py --backend real` — let Opus rewrite the
playbook to cut the stall (push allocation toward the trail) and watch held-out coverage climb off
0.50. Cost: a Haiku episode is cents; an Opus rewrite is ~$1 (the dominant term) — keep the eval lean.

**Settled — don't reopen** (`RESET_DESIGN.md` → "Locked decisions"): the evolved unit is
**English, never code** (that is the sieve that keeps the tacit residue and makes model-generality
the test); **the model orchestrates** (option B), not Python; **Opus** runs self-improvement +
world/oracle reasoning, **Haiku** does all exploration; the judge is the objective coverage band.
The world gate is two halves — **build-screen** model-free for the oracle≫heuristic gap
(`run_anchor.py`), then **calibrate** live so the student lands in-band — re-run both before any
new world ships.

```bash
python run_anchor.py                              # Ch2 build gate: free, model-free, deterministic
pip install pytest && python -m pytest tests/ -q  # tests (pytest is not preinstalled)
python run_loop.py --iterations 1 --backend mock  # the loop, offline (deterministic floor-player)
python run_loop.py --iterations 1 --backend real  # the loop, live (cents/Haiku episode, ~$1/Opus edit)
```

The `claude` CLI is installed and authenticated here, so the `real` backend works without an API
key (subscription auth). The runtime is stdlib-only (Python 3.11); `pytest` is the only dev
dependency.

## Files you'll edit vs. leave alone

Edit now: `hta/config.py` (knobs), `hta/ch2/anchor.py` (the anchor world + oracle + build-screen),
`run_anchor.py` (the build gate), and the **evolvable node `hta/ch2/seed/playbook.md`** (the loop
rewrites *this*; for calibration you may hand-edit the seed). The reseed built the **frozen
substrate** — `hta/ch2/episode_state.py` (world-state machine + band judge), `hta/ch2/probe_server.py`
(confined probe-MCP + the seven primitives), `hta/ch2/loop.py` (the model-orchestrated loop),
`run_loop.py` — leave it alone unless deliberately changing the harness (keep the two invariants).

Leave alone unless deliberately changing them (and then keep the two invariants below): the loop
spine — `hta/archive.py` (archive + selection), `hta/taste.py` (MDL prior), `hta/meta_agent.py`
(Opus self-modify), `hta/sandbox.py` (the meta-agent airgap), `hta/llm.py` (the `claude -p` seam).

## The two invariants (the integrity floor — they survive every chapter)

- **Objective, agent-inaccessible scoring** — worlds are scored by a **dumb deterministic
  function**, never an LLM judge (the agent is optimized *against* the score, so a movable
  score is reward-hacking). *Ch2:* information-weighted **coverage** = cells logically pinned by
  the consistent hypothesis set, normalized into a model-free **floor→oracle band**; the oracle
  is the exact adaptive belief-MDP policy, **by simulation** over the world family
  (`hta/ch2/anchor.py`). The world stays **deterministic** so the oracle is computable.
- **Safe-eval, lifted** — model output never executes. *Ch2:* the evolved artifact is **text**
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
standing permission (no confirmation): green `pytest` (skip for docs-only) → merge the
working branch (fast-forward when possible) → `git push origin main`.
