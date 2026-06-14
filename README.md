# hypertaste

A self-improving **research-taste harness** (DGM-H pipeline). It co-evolves a task agent and
its curriculum so the agent grows **taste** — *choosing your next move well by evaluating your
position* — using that taste as the selection pressure. The agent substrate is
[HyperAgents / DGM-H](https://arxiv.org/abs/2603.19461) — a task agent that investigates the
world plus a meta agent that rewrites the task agent — specialized so that:

- every foundation-model call is a **`claude -p`** call (subscription, no API key);
- **Opus** runs self-improvement and the world/oracle reasoning; **Haiku** does all exploration;
- the world (hidden state + scorer) is **airgapped** from the agent's editable surface — the
  anti-leak wall and the scientific-validity wall at once.

> **Status (2026-06-14).** The settled design is **`DESIGN.md`** (read it first) — taste defined,
> the rules any world must meet, and the machinery. The repo was just cleaned up: the
> **spine** (the world-agnostic orchestration) is kept, the **anchor chapter** is frozen as the
> one worked reference of the airgapped body + mechanical oracle, and the first proof-of-principle
> world (instance 0) was retired as a tactic-not-taste result — see
> `findings/2026-06-14-instance0-machine-world.md`. The next build is a structured world behind the
> existing airgapped body, run against the real loop. The anchor chapter described below is that
> frozen reference; its original design write-up is `history/RESET_DESIGN.md`.

**The docs:** `DESIGN.md` is the design (definition + rules + machinery). `ROADMAP.md` is the
North Star — the two-loop model, the staircase of objective judges, the path to a closed,
hands-off loop. `history/` holds the superseded chapters (`RESET_DESIGN.md`, `PLAN.md`,
`REPLAN.md`, `NEXT.md`) and the Chapter-2 lab log (`NOTEBOOK.md`).

## The three planes

```
┌─ WORLD plane ─ agent-INACCESSIBLE ────────────────────────────────────────────┐
│  hidden state + deterministic coverage scorer + the model-free floor→oracle band │
└──────────────────────── confined probe tools (the airgap) ────────────────────┘
                          │  in: probe(index)   out: value, remaining, cost
┌─ AGENT plane (HyperAgents / DGM-H) ────────────────────────────────────────────┐
│  task agent (Haiku, playbook-driven)  ←─ edited by ─→  meta agent (Opus)        │
│  archive of hyperagents: branch → self-modify → evaluate → re-add               │
└────────────────────────────────────────────────────────────────────────────────┘
┌─ TASTE plane ──────────────────────────────────────────────────────────────────┐
│  band-normalized coverage → fitness (objective, agent-inaccessible)             │
└────────────────────────────────────────────────────────────────────────────────┘
```

The agent reaches the world only through **confined probe tools**, and the evolved unit is an
**English playbook** read as text context — never imported or executed.

## The integrity floor (the two invariants — they survive every chapter)

1. **Objective, agent-inaccessible scoring.** Worlds are scored by a dumb deterministic
   function, never an LLM judge (the agent is optimized *against* the score, so a movable score
   is reward-hacking). Anchor chapter: information-weighted **coverage**, normalized into a
   model-free floor→oracle band, with references by **verified simulation** over the world family.
2. **Safe-eval, lifted.** Model output never executes. The evolved artifact is **text**
   (a playbook); the harness reads node files as context only.

## The spine (the reusable, world-agnostic orchestration)

| File | Role |
|---|---|
| `hta/config.py` | model assignment, knobs, paths |
| `hta/llm.py` | THE seam: `complete` / `episode` / `agentic` `claude -p` adapters, mock backend, accounting |
| `hta/taste.py` | the MDL / program-length prior (generality pressure) |
| `hta/archive.py` | archive of hyperagents + open-ended parent selection |
| `hta/sandbox.py` | meta-agent airgap: Direct (Bash-denied) \| Docker (container); runs the Opus self-modify edit (`hta/ch2/loop.py` `meta_edit`) |

## The anchor chapter (frozen reference)

`hta/ch2/anchor.py` realizes the **trail world**: follow a trail of pointers through a too-large
hypothesis space to a buried landmark, while fat "clearing" claims pay you immediately for going
the wrong way. It is pure **allocation** under a scarce probe budget — every cell is a lookup, so
it cannot compile into a solver. The build-screen (`run_anchor.py`) shows the
belief-MDP **oracle 9.0 ≫ best articulable heuristic 6.0** (gap 0.50 of the floor→oracle band,
controls 0.00) — above the line. It is kept as the one worked example of the airgapped body and
the mechanical oracle; its full design write-up is `history/RESET_DESIGN.md`.

## Quick start

No runtime dependencies beyond the standard library (Python 3.11). The `real` backend requires
the `claude` CLI installed and authenticated with your subscription.

```bash
python run_anchor.py                              # anchor build gate: free, model-free, deterministic
pip install pytest && python -m pytest tests/ -q  # tests (offline; pytest not preinstalled)
python run_loop.py --iterations 1 --backend mock  # the loop, offline (deterministic floor-player)
python run_loop.py --iterations 1 --backend real  # the loop, live (cents/Haiku episode, ~$1/Opus edit)
```

Every run persists its artifacts under `--out-dir`: the archive lineage, a per-iteration
`iter_*.json` audit record (full transcripts + hidden draws, replayable via `loop.score_result`),
and `run.json` (args, history, accounting). Scratch runs default to `outputs/` (gitignored);
curated runs are committed under `runs/` — see `runs/sample-mock/`.

## Airgap / anti-leak design

1. The hidden state lives in the probe server's process and is never importable by the player.
2. The player reaches the world only through confined probe tools (allowlist airgap).
3. The meta agent **only edits the node; it never runs the player against a world**, so it cannot
   observe hidden state. Its workspace holds the editable node + a **sanitized** report.
4. For a hard boundary, run the meta agent in a container (`--sandbox docker`, `hta/sandbox.py`):
   `claude -p` runs **inside** an ephemeral, non-root container with **no repo and no world
   source**, mounting `~/.claude` read-only so it authenticates on the host subscription. It
   **fails closed** if Docker is unavailable. Build once with `scripts/build_agent_image.sh`.
   Default `--sandbox none` keeps the lighter mitigation (Bash denied, in-process).

## Repo map

```
hta/
  config.py            model assignment, knobs, paths
  llm.py               claude -p adapters (complete/episode/agentic) + mock backend + accounting
  taste.py             MDL / program-length prior
  archive.py           archive of hyperagents + open-ended parent selection
  sandbox.py           meta-agent airgap: Direct (Bash-denied) | Docker (container)
  ch2/                 the anchor chapter (frozen reference; design in history/RESET_DESIGN.md)
    anchor.py          the anchor trail world + oracle-by-simulation + the build-screen (generic over
                       a spec protocol, so the oracle/screen re-derive for any world shape)
    worlds.py          the world-smith's structural family: ForkedTrailSpec + the forked/decoy worlds
    world_smith.py     the SECOND loop: ship-gate (hard ∧ solvable ∧ ZPD) + inventor scaffold + demo
    episode_state.py   the frozen world-state machine (the seven primitives) + the band judge
    probe_server.py    confined stdio-MCP server: probe/spawn/submit_map/world_map/remaining/mem_*
    loop.py            the model-orchestrated (option-B) DGM-H loop + the Opus self-modify step (meta_edit)
    seed/playbook.md   the seed evolvable node (non-executable English; Opus rewrites this)
    champion/playbook.md  the recorded gen_0001 disposition (the closed-loop demo's champion)
docker/Dockerfile.agent       agent-plane image (Node + claude CLI; no project code/world/secrets)
scripts/build_agent_image.sh  build the agent-plane image (context = docker/ only)
run_anchor.py          build-screen the anchor family (oracle ≫ heuristic gate + difficulty sweep)
run_loop.py            the model-orchestrated loop (anchor world; mock or real backend)
run_probe.py           stage-1: the champion vs a scalar-harder world (no gap re-opens)
run_worldsmith.py      the world-smith: ship-gate (free) + the live closed-loop demonstration
tests/test_anchor.py        anchor world / oracle / build-screen tests
tests/test_worlds.py        forked-trail structure: the gate-gated lookup + the spec protocol
tests/test_world_smith.py   the ship-gate (ZPD coupling) + the inventor scaffold
tests/test_episode_state.py episode-state machine + band judge (airgap, accounting, spawn carve-out)
tests/test_probe_server.py  probe-MCP framing + role airgap + spawn (offline; injected worker)
tests/test_loop.py          the loop wiring + judge replay + report sanitization (mock)
tests/test_sandbox.py       meta-agent sandbox routing + Docker isolation flags (offline; no daemon)
```

We did not fork [HyperAgents](https://github.com/facebookresearch/Hyperagents)
(CC-BY-NC-SA); this is a lean reimplementation that uses `claude -p` as the model layer. Built on
the concepts of HyperAgents (Zhang et al., 2026) and WILT (Banatt et al., 2025).
