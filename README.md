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

> **Status (2026-06-16).** The current design is **`DESIGN.md`** (read it first) — taste defined,
> the rules any world must meet, and the machinery. The repo is **cut around the system's loops**:
> shared plumbing at the top (`hta/llm.py`, `hta/config.py`), `hta/dgmh/` (grow the agent),
> `hta/gym/` (grow the world), and `hta/world/` (the agent-inaccessible world). The **fresh lab is
> built** (the last pass, `findings/2026-06-16-fresh-lab-world-language.md`): `hta/world/` is the
> **world *language*** (a part-box → `WorldSpec` → a mechanical scorer/oracle), instance 0 is authored
> as a parts-list in it, `hta/dgmh/episode/` + `hta/dgmh/loop.py` are the world-agnostic play + loop,
> and `hta/gym/smith.py` is the world-smith. Run it with `run_lab.py` (screen / loop / smith). The
> retired trail puzzle is still **quarantined** in `hta/_trail/` as the frozen worked reference
> (design write-up `history/RESET_DESIGN.md`) — the fresh lab now carries its own tests, so the trail
> can be deleted in a follow-up. The instance-0 *flat* world was retired earlier as a
> tactic-not-taste result (`findings/2026-06-14-instance0-machine-world.md`).

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
   is reward-hacking). The trail world: information-weighted **coverage**, normalized into a
   model-free floor→oracle band, with references by **verified simulation** over the world family.
2. **Safe-eval, lifted.** Model output never executes. The evolved artifact is **text**
   (a playbook); the harness reads node files as context only.

## Shared plumbing + the machinery (reusable, world-agnostic)

| File | Role |
|---|---|
| `hta/llm.py` | THE seam: `complete` / `episode` / `agentic` `claude -p` adapters, mock backend, accounting |
| `hta/config.py` | model assignment, knobs, paths |
| `hta/dgmh/archive.py` | archive of hyperagents + open-ended parent selection + the MDL / program-length prior |
| `hta/dgmh/sandbox.py` | meta-agent airgap: Direct (Bash-denied) \| Docker (container); runs the Opus self-modify edit |

## The quarantined trail (frozen reference test world)

`hta/_trail/anchor.py` realizes the **trail world**: follow a trail of pointers through a too-large
hypothesis space to a buried landmark, while fat "clearing" claims pay you immediately for going
the wrong way. It is pure **allocation** under a scarce probe budget — every cell is a lookup, so
it cannot compile into a solver. The build-screen (`run_anchor.py`) shows the
belief-MDP **oracle 9.0 ≫ best articulable heuristic 6.0** (gap 0.50 of the floor→oracle band,
controls 0.00) — above the line. It is **quarantined** in `hta/_trail/` as a frozen worked example of
the airgapped body and the mechanical oracle. The fresh lab (`hta/world/` + `hta/dgmh/` + `hta/gym/`)
now carries its own tests and worked instance, so the trail is redundant and can be deleted in a
follow-up; its full design write-up is `history/RESET_DESIGN.md`.

## Quick start

No runtime dependencies beyond the standard library (Python 3.11). The `real` backend requires
the `claude` CLI installed and authenticated with your subscription.

```bash
python run_lab.py screen                              # build-screen the worked worlds: free, model-free
pip install pytest && python -m pytest tests/ -q      # tests (offline; pytest not preinstalled)
python run_lab.py loop --iterations 1 --backend mock  # LOOP 1, offline (deterministic floor-player)
python run_lab.py loop --iterations 1 --backend real  # LOOP 1, live (cents/Haiku episode, ~$1/Opus edit)
python run_lab.py smith                               # LOOP 2 ship-gate (free); + --backend real for the demo
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
4. For a hard boundary, run the meta agent in a container (`--sandbox docker`, `hta/dgmh/sandbox.py`):
   `claude -p` runs **inside** an ephemeral, non-root container with **no repo and no world
   source**, mounting `~/.claude` read-only so it authenticates on the host subscription. It
   **fails closed** if Docker is unavailable. Build once with `scripts/build_agent_image.sh`.
   Default `--sandbox none` keeps the lighter mitigation (Bash denied, in-process).

## Repo map

```
hta/
  llm.py               claude -p adapters (complete/episode/agentic) + mock backend + accounting [shared]
  config.py            model assignment, knobs, paths [shared]
  world/               LOOP target — what a world IS (agent-inaccessible): the WORLD LANGUAGE
    language.py        the part-box (Clearing/Chain/Fork) + WorldSpec + validate + the expander
    grade.py           the world-agnostic engine: dumb coverage scorer, no-inference floor, belief-MDP
                       oracle, the model-free build-screen (the integrity-floor math)
    contract.py        the World interface the engine consumes + the band/score/realize facade
    instances.py       named worlds as parts-lists (instance0 is the worked example) + draw_hstar
  dgmh/                LOOP 1 — grow the AGENT (self-improvement)
    archive.py         archive of hyperagents + open-ended parent selection + the MDL prior
    sandbox.py         meta-agent airgap: Direct (Bash-denied) | Docker (container)
    episode/           the task agent's play + the airgap (generic over a WorldSpec)
      state.py         the world-state machine (the primitives) + the band judge
      server.py        confined stdio-MCP probe server: probe/spawn/submit_map/world_map/remaining/mem_*
    loop.py            the world-agnostic model-orchestrated DGM-H loop + the Opus meta_edit
    seed/playbook.md   the seed evolvable node (non-executable English; Opus rewrites this)
  gym/                 LOOP 2 — grow the WORLD (the curriculum)
    smith.py           the world-smith: ship-gate (hard ∧ solvable ∧ ZPD) + inventor realizer + curriculum
  _trail/              the retired trail puzzle, QUARANTINED as the frozen worked reference (deleted later):
    anchor.py          the trail world + oracle-by-simulation + the build-screen (generic over a spec
                       protocol, so the oracle/screen re-derive for any world shape)
    worlds.py          the world-smith's structural family: ForkedTrailSpec + the forked/decoy worlds
    world_smith.py     the SECOND loop: ship-gate (hard ∧ solvable ∧ ZPD) + inventor scaffold + demo
    episode_state.py   the world-state machine (the seven primitives) + the band judge
    probe_server.py    confined stdio-MCP server: probe/spawn/submit_map/world_map/remaining/mem_*
    loop.py            the model-orchestrated DGM-H loop + the Opus self-modify step (meta_edit)
    seed/playbook.md   the seed evolvable node (non-executable English; Opus rewrites this)
    champion/playbook.md  the recorded gen_0001 disposition (the closed-loop demo's champion)
docker/Dockerfile.agent       agent-plane image (Node + claude CLI; no project code/world/secrets)
scripts/build_agent_image.sh  build the agent-plane image (context = docker/ only)
run_lab.py             THE fresh lab: screen (build-screen instances) | loop (LOOP 1) | smith (LOOP 2)
run_anchor.py          [frozen trail ref] build-screen the trail family (oracle ≫ heuristic gate)
run_loop.py            [frozen trail ref] the model-orchestrated loop on the trail test world
run_probe.py           [frozen trail ref] stage-1: the champion vs a scalar-harder world
run_worldsmith.py      [frozen trail ref] the trail world-smith: ship-gate + the live demonstration
tests/test_world_language.py  the part-box, validator, deterministic expander (composition, the law)
tests/test_world_grade.py     references ordering, above-threshold gate, the ungameable scorer
tests/test_episode.py         episode-state machine + band judge (airgap, accounting, spawn carve-out)
tests/test_episode_server.py  probe-MCP framing + role airgap + spawn (offline; injected worker)
tests/test_dgmh_loop.py       the loop wiring + judge replay + report sanitization (mock)
tests/test_gym_smith.py       the ship-gate (ZPD coupling) + the safe-eval inventor realizer
tests/test_sandbox.py         meta-agent sandbox routing + Docker isolation flags (offline; no daemon)
tests/test_{anchor,worlds,world_smith,episode_state,probe_server,loop}.py  [frozen trail ref] suite
```

We did not fork [HyperAgents](https://github.com/facebookresearch/Hyperagents)
(CC-BY-NC-SA); this is a lean reimplementation that uses `claude -p` as the model layer. Built on
the concepts of HyperAgents (Zhang et al., 2026) and WILT (Banatt et al., 2025).
