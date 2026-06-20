# bet/ — the cheapest test of the whole idea

The bench experiment from `../BET.md`, built. One line:

> **Equip a cheap (Haiku) agent with our framing; race it against the same agent
> without it, on DiscoveryWorld where the path itself is scored; measure the lift.**

Two arms, one toggle. The harness is held fixed; the *only* difference between
arms is the decision discipline the agent runs under:

- **toggle-on** (`playbook.md`) — the operating loop *value → forecast → act →
  revise on the surprise*, plus the two guards (transfer gate + play goal;
  seek the discriminating move).
- **toggle-off** (`baseline.md`) — the same harness with a competent but generic
  "researcher under uncertainty" prompt.

Both are **world-general** — neither names DiscoveryWorld. If the playbook lifts,
it's taste; the instant you tune it to the benchmark you're measuring overfitting.

## The "native Claude Code subagent" realization

The agent is **a native `claude -p` session on Haiku** (not the HTA MCP probe
protocol). Each episode spawns one such session, given:

- the **fixed kickoff** (`prompts.KICKOFF`) — how to drive the world, identical
  both arms;
- the **arm prose** as `--append-system-prompt` — the single toggle;
- **Bash locked to `python dw.py`** (`--allowedTools "Bash(python dw.py:*)"`,
  every file/web/escape tool denied) — so the one thing it can do is act through
  the confined interface.

## The airgap (confined action interface)

```
 harness (run_bet.py)
    │ starts, out-of-band
    ▼
 world server (server.py)  ──holds──►  DiscoveryWorld  (agent-inaccessible)
    ▲  Unix socket, JSON
    │  observe / actions / locations / act     [scorecard = privileged]
 dw.py  (the ONLY tool the agent has, in a clean workdir)
    ▲
 claude -p  (Haiku, per arm)
```

- The world runs in a **separate process**; the agent's workdir holds **only**
  the client (`dw.py` + `rpc.py`) — never the world's source.
- The agent's view is **curated** (`dw_world.agent_view`): task, location,
  things in reach, nearby interactables (terrain filtered), last result. Lean,
  because every observation rides in context every turn (token cost).
- **The score is agent-inaccessible.** The client exposes no score command; the
  `scorecard` command is privileged and only the harness sends it. This is the
  integrity floor — the agent is optimized against the score, so it must not see
  it.

This is the **soft airgap** (in-process tool confinement). Hardening it to a
container (no repo/world mount), like `hta/dgmh/sandbox.py`, is the v2 step.

## Run it

```bash
bash bet/setup_world.sh                                   # clone DiscoveryWorld (gitignored) + deps
python bet/run_bet.py --backend mock --seeds 0,1          # offline, free: exercises the whole pipe
python bet/run_bet.py --backend real --arms on,off --seeds 0,1,2 --max-steps 40   # the live race (Haiku)
python -m pytest tests/test_bet.py -q                     # seam tests (offline, ~6s)
```

`--backend mock` drives the world with a deterministic, *not-smart* policy — it
proves the server/client/budget/scoring plumbing at zero cost (it scores ~0; mock
is plumbing, not taste).

## The measurement

Three mechanical DiscoveryWorld metrics, no LLM judge (`dw_world.scorecard`):

- **`process_score`** (`scoreNormalized`, 0–1) — **the path score**: did you take
  the *right* steps. This is the headline metric; it dissolves the path-vs-answer
  tension BET.md worries about.
- **`completed_successfully`** — task completion (binary).
- knowledge — `criticalQuestions` (carried, not yet auto-graded here).

The v1 gate: **toggle-on beats toggle-off** on held-out parametric variations
(each seed is a different layout/data/solution). `run_bet.py` prints the per-arm
means and the lift.

## Cost & calibration

- A short real episode (8 moves, Proteomics/Normal) ≈ **$0.11**, ~90s, ~12 turns.
  A 40-move episode costs more (context grows); budget by the **move count**, the
  scarce resource — turns get headroom.
- **First real datapoint** (toggle-on, 8 moves): the agent picked up the meter,
  analyzed an animal, and scored **process=0.25 (2/8)** — low-but-nonzero, the
  band BET.md item 2 asks for. 8 moves is budget-starved; a real run wants ~30–50.
- A full race (2 arms × ~5 seeds × ~40 moves) is order **$5–10**. That's a
  real-money run — choose scenario/difficulty/budget deliberately before firing.

## What this resolves vs. BET.md's open items

| BET item | here |
|---|---|
| 1. playbook prose | `playbook.md` / `baseline.md` — first cut; tune on the bench |
| 2. difficulty band | seam + scorecard in place to calibrate; first probe shows low-but-nonzero |
| 3. confined action interface | **done** — server/client airgap, agent-inaccessible score |
| 4. run protocol | `run_bet.py` multi-seed/two-arm + lift report; win-margin/N still to set |
| 5. generator + v2 purity arm | deferred, as named |

## Files

| file | role |
|---|---|
| `dw_world.py` | the world: load headless, curated view, act+tick, out-of-band score |
| `server.py` | holds one episode behind a Unix socket; privileged `scorecard` |
| `dw.py` | the confined client — the only thing the agent runs |
| `rpc.py` | the socket wire (newline JSON) |
| `prompts.py` | fixed kickoff + arm-prose loader (the toggle) |
| `playbook.md` / `baseline.md` | toggle-on / toggle-off decision discipline |
| `episode.py` | one episode: server + agent (real `claude -p` / mock) + score |
| `run_bet.py` | the harness: multi-seed two-arm race + lift report |
| `setup_world.sh` | clone DiscoveryWorld (gitignored) + deps |
