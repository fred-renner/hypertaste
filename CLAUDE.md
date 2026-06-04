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
