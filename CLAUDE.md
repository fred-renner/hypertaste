# CLAUDE.md

Guidance for Claude Code working in this repository.

## Orientation

`hypertaste` is a self-improving research-taste harness (DGM-H pipeline): it co-evolves a
task agent and its curriculum on a "discover the hidden rule by probing" world.

- Architecture and run instructions: `README.md`.
- Long-term direction (the two-loop model, staircase of judges, closing the loop): `ROADMAP.md`.
- World-growth design and rationale for *today's* world (Chapter 1): `WORLD_DESIGN.md`.

This file plus `README.md` are the orientation — open only the files you're about to
change rather than re-reading the whole tree. `ROADMAP.md` is the direction; `WORLD_DESIGN.md`
is the current chapter's mechanics.

## Run & test

```bash
python run_loop.py --iterations 5 --backend mock          # free, deterministic, fast
python run_loop.py --iterations 5 --backend real --episode-mode single_session \
  --max-probes 6 --n-train 2 --n-transfer 1                # real; episodes run concurrently

pip install pytest && python -m pytest tests/ -q          # pytest is not preinstalled
```

The `claude` CLI is installed and authenticated here, so the `real` backend works without
an API key (subscription auth). The runtime is stdlib-only (Python 3.11); `pytest` is the
only dev dependency. Shared CLI args live in `run_iteration.add_common_args`; `run_loop.py`
adds `--iterations`.

## Files you'll edit vs. leave alone

Edit: `hta/config.py` (knobs), `hta/loop.py` (iteration), `hta/task_agent.py` (eval),
`hta/world/world_smith.py` (curriculum), `hta/seed/*` (the evolving program + prompts the
meta agent rewrites).

Leave alone unless you are deliberately changing the scorer (`engine.py`), the safe-eval
whitelist (`grammar.py`), or the probe airgap (`channel.py`) — and if you do, keep the
two invariants below.

## The two invariants

- **Objective scoring** — worlds score guesses by empirical equivalence on a fixed
  battery (`hta/world/engine.py`). Keep rules pure deterministic `f(x,y,z) → bool`.
- **Safe-eval** — every rule string is AST-validated against a strict whitelist and `eval`'d
  with no builtins (`hta/world/grammar.py`); model output can't run code.

## Gotchas

- `single_session` episodes are real-backend only; mock uses `per_probe`.
- Eval runs episodes concurrently on the real backend (`eval_concurrency`).
- The episode turn budget is `max_probes*2 + buffer`, so probes (not turns) bind.
- `--sandbox none` is the soft airgap (Bash denied, in-process); `--sandbox docker` is the
  hard one (slower, same token cost) — it runs the meta agent in a container with no repo
  or world source, mounting `~/.claude` read-only so it auths on the host subscription.
- A non-solving agent that spends all its probes is a legitimate worst-score failure —
  worlds are gated to be solvable within budget, so we don't rescue it.

## Token efficiency

Token efficiency matters at every level:

- **The harness:** every `claude -p` call carries a fixed ~31k-token system-prompt tax, so
  minimize call *count* (prefer single-session episodes over per-probe), keep prompts and
  the eval report lean, and don't multiply cost (e.g. `eval_repeats`) without a staged-eval
  gate to cap it.
- **The code:** prefer the smallest design that meets the need; delete dead paths and stale
  docs rather than letting them accrue.
- **Working style:** be concise, parallelize independent tool calls, don't re-read files,
  don't pad explanations.
- **Answers:** lead with the verdict (do/skip + the action), back claims with `file:line`,
  recommend rather than offload the decision, keep caveats short and last, and don't
  frontload detail that wasn't asked for — expand on request.

Order of magnitude: a Haiku task call/episode is a few cents; an Opus meta-agent edit is
~$1 and dominates the cost of a real iteration. Call out the token/cost impact of changes.

## Finalizing work — always land on `main`

A task is not finished until it is merged into `main` and `main` is pushed to origin.
Pushing only a feature branch is not "done". When the session's work is complete, merge to
`main` and push it **without asking for confirmation** — this is standing permission; just
do it as the final step.

1. Develop on a working branch and commit there.
2. Run `python -m pytest tests/ -q` and make it green (skip only for docs-only changes).
3. Merge the working branch into `main` (fast-forward when possible) and `git push origin main`.
