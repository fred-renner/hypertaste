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

> Status: **testing mode**. Classic numeric WILT, one-iteration pipeline verified
> end-to-end on both the offline mock backend and live `claude -p`. See *Status* below.

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

### The two `claude -p` adapters (`hta/llm.py`)
- `complete(prompt, model, role)` → `claude -p <prompt> --model M --output-format json --max-turns 1`.
  No tools granted ⇒ behaves like a text completion. Output is unwrapped from the JSON
  `result` field and de-fenced.
- `agentic(instruction, workdir, model, allowed_tools, max_turns)` → `claude -p` run
  **inside the child workspace** with `Edit/Read/Write` and `--permission-mode acceptEdits`.
  **Never granted Bash**, never run where the world source is reachable.

## Quick start

No runtime dependencies beyond the standard library. The `real` backend requires the
`claude` CLI installed and authenticated with your subscription.

```bash
# Deterministic, free, offline — verifies the whole pipeline:
python run_iteration.py --backend mock
python run_loop.py --iterations 5 --backend mock

# Live claude -p (Haiku task agent, Opus meta + world-smith). Start small:
python run_iteration.py --backend real --max-probes 5 --n-train 1 --n-transfer 1

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
4. Any model-generated lambda (candidate, world-smith rule, or agent guess) is
   AST-validated against a strict whitelist and evaluated with no builtins
   (`hta/world/grammar.py`) — model output cannot execute arbitrary code.
5. For production, run the agent plane in a container (as HyperAgents does); the meta
   agent is denied Bash here as a lighter mitigation.

## Cost / throughput finding

Each `claude -p` call carries ~31k tokens of cached Claude-Code system-prompt overhead
(~$0.04 per Haiku call) because we use the CLI as a generation engine. That is the main
scaling constraint (roadblocker #3). Mitigations in place: Haiku task agent, tiny
testing profile, objective local scoring (no LLM in the scoring path). Recommended next
optimization: run an entire probing episode as **one** `claude -p` session (channel
exposed as a tool) so the system-prompt tax is amortized across probes instead of paid
per probe.

## Roadblockers → how they're handled

| Roadblocker | Handling |
|---|---|
| `claude -p` is an agent, not a completion endpoint | two adapters: constrained (task/world) vs agentic (meta) |
| Reward-hacking / leaking the hidden rule | airgap: meta edits code but never runs eval; sanitized report; ProbeChannel only |
| Subscription throughput / cost | Haiku task agent; minimal calls; objective scoring; (next) single-session episodes |
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
  loop.py              one DGM-H iteration (parent eval → self-modify → child eval)
  seed/
    solver.py          seed editable task-agent program (STRATEGY knob)
    meta_strategy.md   editable meta playbook (metacognitive self-modification)
  world/               AGENT-INACCESSIBLE
    grammar.py         safe lambda compilation + candidate hypothesis library
    channel.py         ProbeChannel — the only agent↔world interface
    engine.py          WiltWorld: hidden rule + empirical-equivalence scorer + info gain
    world_smith.py     Opus curriculum generator + frozen transfer suite
run_iteration.py       run one iteration, report improvement + cost
run_loop.py            run N iterations, print progression
tests/test_pipeline.py mock end-to-end + airgap + sandbox tests
```

Built on the concepts of HyperAgents (Zhang et al., 2026) and WILT (Banatt et al., 2025).
