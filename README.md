# hypertaste

A self-improving **research-taste harness**. It co-evolves a curriculum and a
self-modifying agent, using *research taste* as the selection pressure, on a
[WILT](https://arxiv.org/abs/2410.10998)-style "discover the hidden rule by probing"
world. The agent substrate is [HyperAgents / DGM-H](https://arxiv.org/abs/2603.19461)
(a task agent that solves the task + a meta agent that rewrites the task agent **and
its own improvement procedure**), specialized so that:

- every foundation-model call is a **`claude -p`** call (subscription, no API key);
- the **task agent runs on Haiku**, the **meta agent and world-smith run on Opus**;
- the world (hidden rule + scorer) is **airgapped** from the agent's editable surface,
  which is simultaneously the anti-leak wall and the scientific-validity wall.

> Status: **Chapter 1 (classic numeric WILT) — this is what the loop runs.** Multi-iteration
> evolution is verified end-to-end on both backends (offline mock + live `claude -p`);
> episodes run concurrently and lineage compounds. But Chapter 1's binary judge gave a *flat*
> taste signal (recover the rule exactly or score ~nothing), so the project has **pivoted to
> Chapter 2 — a navigable investigation-map judged by coverage** (`WORLD_DESIGN.md`). The
> Chapter-2 **thin de-risking slice is built** (`hta/ch2/`, `python run_slice.py`): it confirms
> the *ramp* bet but shows the first maps are too transparent for a Haiku taste-gap — the next
> step is **deception** before the loop (`WORLD_DESIGN.md` → "First slice"). This README
> documents the running Chapter-1 code.

**Where it's going:** `ROADMAP.md` is the North Star — the two-loop model (worlds
self-evolve to the student's edge; judges change between chapters as taste saturates), the
staircase of objective judges, and the staged path to a closed, hands-off loop. This
README documents the *running Chapter-1 code*; `WORLD_DESIGN.md` is the **Chapter-2 design**
we're building toward; `ROADMAP.md` is the arc.

## The three planes

```
┌─ WORLD plane (Opus world-smith + WILT engine) ─ agent-INACCESSIBLE ──────────┐
│  hidden rule λ + scorer + curriculum + frozen held-out transfer set          │
└──────────────────── narrow append-only probe channel ───────────────────────┘
                          │  in: [x,y,z]   out: True/False, attempts-left
┌─ AGENT plane (HyperAgents / DGM-H) ──────────────────────────────────────────┐
│  task agent (Haiku)  ←─ edited by ─→  meta agent (Opus)                       │
│  archive of hyperagents: branch → self-modify → evaluate → re-add             │
└──────────────────────────────────────────────────────────────────────────────┘
┌─ TASTE plane (world-independent) ────────────────────────────────────────────┐
│  info-gain · falsification · novelty · Occam · transfer → composite fitness   │
└──────────────────────────────────────────────────────────────────────────────┘
```

The probe channel (`hta/world/channel.py`) is the **only** crossing point between the
agent and the world. The agent learns one boolean per probe and nothing else.

## Where the LLM calls are (model assignment)

Every call funnels through `hta/llm.py`. There are exactly three call sites:

| Call site | File | `claude -p` mode | Model | Volume |
|---|---|---|---|---|
| Task agent: probe + guess | `hta/task_agent.py` → `hta/seed/solver.py` | **constrained** (`--max-turns 1`, no tools) | **Haiku** (`task_model`) | high (per probe + guess) |
| Meta agent: self-modify code | `hta/meta_agent.py` | **agentic** (`Edit/Read/Write`, `acceptEdits`) | **Opus** (`meta_model`) | 1 / iteration |
| World-smith: grow curriculum | `hta/world/world_smith.py` | **constrained** | **Opus** (`world_model`) | 1 / iteration |

Reassign via env vars or CLI flags:
```bash
HTA_TASK_MODEL=haiku  HTA_META_MODEL=opus  HTA_WORLD_MODEL=opus  HTA_BACKEND=real
# or: python run_iteration.py --backend real --task-model haiku --meta-model opus
```

### The three `claude -p` adapters (`hta/llm.py`)
- `complete(prompt, model, role)` → `claude -p <prompt> --model M --output-format json --max-turns 1`.
  No tools granted ⇒ behaves like a text completion. Output is unwrapped from the JSON
  `result` field and de-fenced. (per-probe task agent + world-smith)
- `episode(prompt, model, mcp_server_argv, server_env, ...)` → runs a **whole world's episode in
  one `claude -p` session** with the probe channel exposed as a narrow stdio-MCP tool
  (`hta/world/probe_server.py`). The ~31k-token system-prompt overhead is paid **once per world**
  instead of once per probe. Only `mcp__probe__*` tools are allowed; Bash/Read/Edit/Write are
  denied (airgap). (single-session task agent — the efficient mode)
- `agentic(instruction, workdir, model, allowed_tools, max_turns)` → `claude -p` run
  **inside the child workspace** with `Edit/Read/Write` and `--permission-mode acceptEdits`.
  **Never granted Bash**, never run where the world source is reachable. (meta agent)

### Task-agent execution modes (`episode_mode`)
- `per_probe` (default; used by the mock/tests): one `complete()` call per probe.
- `single_session`: one `episode()` per world — the efficient path. **Contamination boundary:**
  context is shared *within* a world's episode (the multi-turn memory we want) but a **fresh
  session is used per world** (never across worlds → no hypothesis bleed / rule-distribution leak)
  and never across roles. The only tool the session can use is the probe channel.

## Quick start

No runtime dependencies beyond the standard library. The `real` backend requires the
`claude` CLI installed and authenticated with your subscription.

```bash
# Deterministic, free, offline — verifies the whole pipeline:
python run_iteration.py --backend mock
python run_loop.py --iterations 5 --backend mock

# Live claude -p (Haiku task agent, Opus meta + world-smith). Start small:
python run_iteration.py --backend real --max-probes 5 --n-train 1 --n-transfer 1

# Efficient task agent: whole episode per world in one claude -p session (MCP probe tool):
python run_iteration.py --backend real --episode-mode single_session --max-probes 8 --n-train 1 --n-transfer 1

# Tests (mock only, incl. airgap + sandbox checks):
python -m pytest tests/ -q
```

Useful flags: `--profile testing|full`, `--max-probes`, `--n-train`, `--n-transfer`,
`--meta-max-turns`, `--task-model/--meta-model/--world-model`, `--out-dir`.
Archive + node metadata are written under `outputs/archive/gen_XXXX/`.

## What "research taste" means here (the fitness)

Defined in `hta/taste.py`, computed **objectively** (no LLM judge, which would be
gameable). For each world:

```
fitness = 0.50·solved      # exact, Occam-correct rule recovery (empirical equivalence)
        + 0.20·agreement   # fraction of a held-out battery the guess matches
        + 0.15·info_gain   # avg hypothesis-space reduction per probe
        + 0.10·novelty     # 1 − probe reuse (anti doom-loop)
        + 0.05·occam       # simplicity of the final guess
```

Train fitness and **frozen transfer** fitness (held-out world families the smith never
adapts) are averaged, so improvement must be *general* taste, not curriculum overfit.

## Airgap / anti-leak design

1. The hidden rule, its source, and the scorer live in `hta/world/` and are never
   importable from the solver (the agent program imports nothing from `hta.world`).
2. The agent reaches the world only through `ProbeChannel` → booleans only.
3. The meta agent **only edits code; it never executes the solver against a world**, so
   it cannot observe a hidden rule. Its workspace contains just the editable program +
   a **sanitized** eval report (the agent's own probes/booleans/guesses — never rule
   names or sources; enforced by a test).
4. **Safe-eval** (a separate guard, not the airgap): any model-generated lambda
   (candidate, world-smith rule, or agent guess) is AST-validated against a strict
   whitelist and evaluated with no builtins (`hta/world/grammar.py`) — model output
   cannot execute arbitrary code.
5. For a hard boundary, run the self-modifying meta agent in a container
   (`--sandbox docker`, see `hta/sandbox.py`): `claude -p` runs **inside** an ephemeral,
   non-root, resource-limited container with **no repo and no `hta/world/*`** — the child
   workspace is copied in, edited, the result copied out, the container destroyed. We
   airgap the **world, not the infra**: the container mounts `~/.claude` read-only so it
   authenticates on the host subscription (the token is not the secret — the hidden rule
   is). It **fails closed** if Docker is unavailable. Build once with
   `scripts/build_agent_image.sh`. Default `--sandbox none` keeps the lighter mitigation
   (Bash denied, in-process).

## Cost / throughput finding

Each `claude -p` call carries ~31k tokens of cached Claude-Code system-prompt overhead
(~$0.02–0.04 per Haiku call) because we use the CLI as a generation engine — the main
scaling constraint (roadblocker #3). **`episode_mode=single_session` addresses it**: a whole
world's episode (all probes + guess) runs in **one** `claude -p` session via the stdio-MCP
probe tool, so that overhead is paid **once per world** instead of once per probe. The win
grows with `max_probes` (per-probe cost is linear in probes; single-session is ~flat). Other
mitigations: Haiku task agent, objective local scoring (no LLM in the scoring path).

Measured A/B (same world, smart strategy, `max_probes=6`, live Haiku):

| mode | claude -p calls | cost | solved | fitness |
|---|---|---|---|---|
| `per_probe` | 7 | $0.1890 | ✓ | 0.879 |
| `single_session` | 1 | $0.0405 | ✓ | 0.888 |

~4.7× cheaper at 6 probes; the ratio grows toward ~30× at the full 30-probe WILT budget.

With single-session episodes and concurrent eval in place, the Opus meta agent dominates
per-iteration cost. Staged-eval gating (eval a child on one world first, full set only if
it clears a bar) and diagnose-from-sampled-failure (hand the meta agent one sampled failing
trajectory instead of the whole report) are the main remaining levers; neither is implemented yet.

## Roadblockers → how they're handled

| Roadblocker | Handling |
|---|---|
| `claude -p` is an agent, not a completion endpoint | two adapters: constrained (task/world) vs agentic (meta) |
| Reward-hacking / leaking the hidden rule | airgap: meta edits code but never runs eval; sanitized report; ProbeChannel only; optional `--sandbox docker` hard boundary (no repo or world source in the meta agent's container) |
| Subscription throughput / cost | Haiku task agent; objective scoring; **single-session episodes** (`episode_mode=single_session`) amortize the ~31k system-prompt tax to once per world |
| Overfitting vs world-independent taste | frozen transfer suite averaged into fitness |
| Operationalizing "taste" without Goodhart | objective metrics; LLM judgement only on the world-generation side |
| Arbitrary code from model strings | strict AST whitelist + no-builtins eval |

## Repo map

```
hta/
  config.py            model assignment, knobs, fitness weights, paths
  llm.py               THE seam: constrained + agentic claude -p, mock backend, accounting
  taste.py             taste metrics + composite fitness
  task_agent.py        load + run the editable solver; sanitized report
  meta_agent.py        Opus agentic self-modification (+ deterministic mock)
  archive.py           archive of hyperagents + open-ended parent selection
  sandbox.py           meta-agent airgap strategies: Direct (Bash-denied) | Docker (container)
  loop.py              one DGM-H iteration (parent eval → self-modify → child eval)
  world/               AGENT-INACCESSIBLE
    grammar.py         safe lambda compilation + candidate library + sampled hypothesis space
    channel.py         ProbeChannel — the only agent↔world interface
    engine.py          WiltWorld: hidden rule + empirical-equivalence scorer + info gain
    world_smith.py     Opus curriculum generator (ZPD + weak-tag targeting, compositional
                       worlds, solvability + novelty gates) + independently-seeded transfer
    probe_server.py    stdlib stdio-MCP server: exposes ONE world as narrow probe tools
  seed/
    solver.py          seed task-agent program (STRATEGY knob; run() + episode_prompt())
    episode_prompt.md  editable single-session strategy surface (meta agent edits this)
    meta_strategy.md   editable meta playbook (metacognitive self-modification)
docker/
  Dockerfile.agent     agent-plane image (Node + claude CLI; no project code/world/secrets)
scripts/build_agent_image.sh  build the agent-plane image (context = docker/ only)
run_iteration.py       run one iteration, report improvement + cost (shared CLI args)
run_loop.py            run N iterations, print progression
tests/test_pipeline.py mock end-to-end + airgap + probe-server + curriculum tests
tests/test_world_design.py  compositional worlds + sampled hypothesis space + solvability/novelty gates
tests/test_sandbox.py  meta-agent sandbox routing + Docker isolation flags (offline; no daemon)
```

We did not fork [HyperAgents](https://github.com/facebookresearch/Hyperagents)
(CC-BY-NC-SA); this is a lean reimplementation that uses `claude -p` as the model layer.
Built on the concepts of HyperAgents (Zhang et al., 2026) and WILT (Banatt et al., 2025).
