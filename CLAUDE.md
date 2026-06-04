# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Finalizing work — always land on `main`

**A task is not finished until it is merged into `main` and `main` is pushed to
origin.** Pushing only a feature branch is not "done".

Standard flow:
1. Develop on a working branch and commit there.
2. Run the test suite (`python -m pytest tests/ -q`) and make it green.
3. Merge the working branch into `main` (fast-forward when possible) and
   `git push origin main`.

So the last step of completing any task is always: merge into `main`, push `main`.

## Token efficiency is a first-class concern

The maintainer cares about token efficiency **in general** — apply it at every level:

- **In the harness it builds:** every `claude -p` call carries a fixed ~31k-token
  system-prompt tax, so minimize call *count* (prefer single-session episodes over
  per-probe), keep prompts and the meta agent's eval report lean, and don't multiply
  cost (e.g. `eval_repeats`) without a staged-eval gate to cap it.
- **In the code itself:** prefer the smallest design that meets the need; delete dead
  paths and stale docs rather than letting them accrue.
- **In your own working style:** be concise, parallelize independent tool calls, avoid
  re-reading files you've already read, and don't pad explanations.

When proposing changes, call out the token/cost impact explicitly.

## Operating notes (skip the warmup — don't re-explore the repo each session)

This file + `README.md` ARE the orientation. Don't read the whole tree to get your
bearings; open only the files you're about to change. The map below is enough to act.

**Environment (this managed remote):**
- The `claude` CLI is installed and authenticated — the `real` backend works out of the
  box. No API key needed (subscription auth).
- `pytest` is NOT preinstalled: `pip install pytest` once, then `python -m pytest tests/ -q`
  (26 tests, ~2s, mock-only so free). Runtime itself is stdlib-only (Python 3.11).
- Cost reality (so you can judge spend): ~$0.02–0.03 per Haiku call/episode; **~$1 per
  Opus meta-agent edit** — the meta agent is ~77% of run cost. World reasoning is cheap.

**Run it:**
```bash
python run_loop.py --iterations 5 --backend mock          # free, deterministic, fast
python run_loop.py --iterations 5 --backend real --episode-mode single_session \
  --max-probes 6 --n-train 2 --n-transfer 1                # real; episodes run concurrently
```
Shared CLI args live in `run_iteration.add_common_args`; `run_loop.py` adds `--iterations`.

**Pipeline in one breath:** `loop.run_iteration` → world-smith builds train+transfer worlds
→ eval PARENT → meta agent rewrites a CHILD → eval CHILD → archive + report. Foundation-model
calls funnel through `hta/llm.py` (`complete`/`episode`/`agentic`); the airgapped world lives
in `hta/world/`; fitness in `hta/taste.py`.

**Files you'll actually edit:** `hta/config.py` (knobs), `hta/loop.py` (iteration),
`hta/task_agent.py` (eval), `hta/world/world_smith.py` (curriculum), `hta/seed/*` (the
evolving program + prompts the meta agent rewrites). Leave `hta/world/{engine,grammar,channel}.py`
alone unless changing the scorer/airgap (and then mind the two invariants below).

**Gotchas:** `single_session` episodes are real-backend only (mock uses `per_probe`); eval is
concurrent on the real backend (`eval_concurrency`); the meta agent's turn budget defaults to
40 but uses ~14–27; episode turn budget is `max_probes*2 + buffer` so probes (not turns) bind;
`--sandbox none` is the soft airgap (Bash denied, in-process), `docker` is the hard one (slower,
same token cost). A non-solving agent that uses all its probes is a legitimate worst-score
failure — worlds are gated to be solvable within budget, so we don't "rescue" it.

## Project orientation

`hypertaste` is a self-improving research-taste harness (DGM-H pipeline). Key docs:
- `README.md` — architecture, the LLM-call map, the airgap model, run instructions.
- `WORLD_DESIGN.md` — how the world grows (Axes A + B; first slice implemented).
- `HANDOFF.md` — current status and next steps.
- `REFERENCE.md` — what we borrow from HyperAgents.

Two invariants must hold for any world change (see `WORLD_DESIGN.md`):
- **Objective scoring** — worlds score guesses by empirical equivalence on a fixed
  battery (`hta/world/engine.py`); keep rules pure deterministic `f(x,y,z)→bool`.
- **Airgap** — every rule string is AST-validated against a strict whitelist and
  `eval`'d with no builtins (`hta/world/grammar.py`); model output can't run code.
