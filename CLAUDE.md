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
`run_loop.py`. Offline-green (46 tests), **calibrated live**, and the **agent loop is validated**: one
real iteration took the seed → gen_0001 (the coach *discovered* the withheld allocation note on its
own) and held-out coverage climbed **0.50 → 1.00** (see below).

**Next action — THE WORLD-SMITH (the second loop)** (`ROADMAP.md` → closing the loop):

The agent loop is proven: `run_loop.py --backend real` took seed → gen_0001 and the coach (Opus)
*discovered* the withheld allocation note ("list every chain, count payoff-per-dig, commit to the
deepest"); held-out coverage went **0.50 → 1.00**. A stage-1 probe (`run_probe.py`) then asked whether
*scalar*-hardening the **same** world re-opens a gap: it does not. Every gated dial-setting keeps the
**same** optimal policy (walk the trail) — only the stakes move (best greedy heuristic pinned at 6,
only the oracle scales) — so a knob can't make the champion's strategy *wrong*; it holds (3/4 perfect,
1/4 a budget-slack execution strand). The gradient now lives in the **world's structure**, not the dials.

So build the **world-smith**: the curriculum half that *evolves the world's structure* — a deeper /
branching / adaptive trail, **never a knob** — to demand a kind of taste the player **does not yet
have**, accounting for what the last run surfaced (e.g. the strand under budget slack → a world that
punishes blind full-commitment, where the new note must be *scout feasibility, then commit*). First
deliverable is the closed-loop demonstration: author a structurally harder world, show the champion
**fails by strategy** (not luck), run one coaching round, show the new player **passes**. **Budget
co-evolves with the world** — as new behaviors need more steps the step budget may grow — but stays
**tight** (scarcity is the point; probes, not turns, bind). Keep both invariants below; fresh session, with a plan.

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
python run_probe.py --backend real                # stage-1: champion vs a scalar-harder world (cents)
```

The `claude` CLI is installed and authenticated here, so the `real` backend works without an API
key (subscription auth). The runtime is stdlib-only (Python 3.11); `pytest` is the only dev
dependency.

## Files you'll edit vs. leave alone

Edit now: `hta/config.py` (knobs), `hta/ch2/anchor.py` (the anchor world + oracle + build-screen),
`run_anchor.py` (the build gate), `run_probe.py` (stage-1 champion-vs-harder-world probe), and the
**evolvable node `hta/ch2/seed/playbook.md`** (the loop
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
  *Lifted to the second loop (the world-smith):* the same wall holds one level up — **the inventor
  proposes only the world's *structure*, never the score.** The referee (coverage) and the
  perfect-play benchmark (oracle) are **re-derived mechanically** from that structure, and a world
  ships only if it is still **hard** (oracle ≫ greedy) **and solvable** within budget. An inventor
  that could also move the score would just mint worlds that *look* solved — the exact trap that
  forced the reset.
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
