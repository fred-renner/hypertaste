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
`run_loop.py`. Offline-green (66 tests), **calibrated live**, the **agent loop is validated** (seed →
gen_0001, the coach *discovered* the withheld allocation note on its own, held-out **0.50 → 1.00**),
and the **world-smith (the second loop) is built and validated live** (`hta/ch2/worlds.py`,
`hta/ch2/world_smith.py`, `run_worldsmith.py`) — the machinery **runs and extends**, but the live run
surfaced a finding (below) that reframes the next step.

**Where the world-smith stands.** A stage-1 probe (`run_probe.py`) showed no *scalar* crank of the
anchor re-opens a gap — "list every chain, commit to the deepest" survives every dial, so the gradient
lives in the world's **structure**. So the world-smith authors a structurally harder world — the
**forked trail** (`worlds.decoy_spec`): two candidate chains and a **gate** whose hidden value says
which is live, so committing to a chain without the cheap gate scout pins **zero** valley, whichever
chain it is. The new taste it demands is **scout feasibility, then commit**. The integrity wall is
lifted intact: the inventor proposes only **structure** (a validated spec as *data* — safe-eval
lifted, never the score), and the harness re-derives the oracle + coverage **mechanically** (the
unchanged `anchor.py` machinery) and ships a world only if **hard** (oracle ≫ every generic planner) ∧
**solvable** (a reachable *method* reaches the oracle) ∧ in the **ZPD** (the champion's method *fails*
while the new one *succeeds* — the only legal coupling is the objective gap on the non-movable scorer,
never the agent's internals). **Model-free proven** (`run_worldsmith.py`, free, deterministic): the
decoy **ships** (gap 0.71n, champion 0.00n, fix 1.00n) and its **second move extends the family** — the
adaptive **gate ladder** (`worlds.ladder_spec`, `gate_hops`): the live chain is chosen by a *ladder* of
gates, so the decoy's own fix ("scout *the* gate") now fails and only "scout *adaptively*, then commit"
ships (gap 0.83n, champion 0.00n, fix 1.00n). A `CURRICULUM` runs the moves in sequence, each graduate
the next champion. A no-fork control correctly *holds* — the SAME method, broken precisely by each move.

**Live run (2026-06-09, $2.47): machinery runs + extends, gap did NOT close — the finding for the next
session.** Both moves shipped, the ladder was authored and slotted into the curriculum, and the
two-iteration two-loop ran live end-to-end with each graduate carried forward (iter 1 decoy 0.00n→0.00n;
iter 2 ladder 0.33n→0.00n). The extensibility was the deliverable and it holds; the **gap-closing did
not**, and *why* is a research-taste finding: **the model-free proxy is not faithful to the live
student.** The proxies model an *allocation/scout* failure, but live Haiku **already scouts** (gate and
ladder, off `world_map`); it fails on the **pointer-chase reconstruction** the score rewards (follow
`head → hop[value] → landmark`, submit the valley off the *true* landmark — it mis-resolves ~half the
time, `determined=9` but `raw=0`). And **coaching regressed the player**: Opus diagnosed the pointer bug
precisely but kept a "bank what's certain" hedge that, against an *all-or-nothing valley*, trades the
valley for the floor (`coached_1` solved 2/4; the hedge dropped its graduate to 0). The integrity wall
did its job — surfacing, honestly, that *the proxy we can compute ≠ the constraint that binds the live
student*.

**Next action — GENERAL-STATE BRAINSTORM (next session), then proceed.** Not more live runs yet. The
open question: make the model-free ship-gate **faithful to the live student** so "champion fails" means
the *same thing* live — the precondition for the loop's closure to mean anything. Live-discussed forks
(your call next session): (a) **fix the coach** — kill the hedge, foreground that the valley is
all-or-nothing, allow multi-round coaching (cheapest test; `coached_1`'s 2/4 suggests a non-hedging
playbook gets ~halfway); (b) **realign the world** — partial credit for partial pointer-chains, or
harden reconstruction (K>2 so mis-resolution self-detects) so the modeled gap *is* the live gap; (c)
**step back to the student's floor** — harden pointer-chase reconstruction on the single anchor first,
then re-run the curriculum. Keep both invariants below; **budget co-evolves but stays tight** (probes,
not turns, bind).

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
python run_worldsmith.py                          # ship-gate both curriculum moves: free, model-free (slow: the ladder oracle is 4096 hyps)
python run_worldsmith.py --backend real           # + the LIVE two-iteration two-loop (~$1/Opus coaching round; ~$2.5 total)
```

The `claude` CLI is installed and authenticated here, so the `real` backend works without an API
key (subscription auth). The runtime is stdlib-only (Python 3.11); `pytest` is the only dev
dependency.

## Files you'll edit vs. leave alone

Edit now: `hta/config.py` (knobs), `hta/ch2/anchor.py` (the anchor world + oracle + build-screen — now
generic over a spec *protocol* so the oracle/screen re-derive mechanically for any world shape),
`hta/ch2/worlds.py` (the world-smith's structural family — `ForkedTrailSpec` with the adaptive gate
ladder `gate_hops`; the forked/decoy/ladder worlds), `hta/ch2/world_smith.py` (the second loop —
ship-gate, the scout/ladder methods, inventor scaffold + the `CURRICULUM` two-iteration demo),
`run_anchor.py` (the build gate), `run_probe.py` (stage-1 scalar-harder probe), `run_worldsmith.py`
(the world-smith demo), and the **evolvable node `hta/ch2/seed/playbook.md`** (the loop rewrites
*this*; for calibration you may hand-edit the seed). The reseed built the **frozen substrate** —
`hta/ch2/episode_state.py` (world-state machine + band judge), `hta/ch2/probe_server.py` (confined
probe-MCP + the seven primitives), `hta/ch2/loop.py` (the model-orchestrated loop), `run_loop.py` —
leave it alone unless deliberately changing the harness (the world-smith touched it *minimally*:
`world_map`/report/serialization now delegate to the spec so a richer world rides the same airgap; the
coverage judge and the text artifact are untouched — both invariants intact).

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
