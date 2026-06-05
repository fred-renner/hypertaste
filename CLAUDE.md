# CLAUDE.md

Guidance for Claude Code working in this repository.

## Orientation

`hypertaste` is a self-improving research-taste harness (DGM-H pipeline): it co-evolves a
task agent and its curriculum on a "discover the hidden rule by probing" world.

- Architecture and run instructions for the **running code** (still Chapter 1): `README.md`.
- Long-term direction (the two-loop model, staircase of judges, closing the loop): `ROADMAP.md`.
- World-growth design and rationale for the **current chapter** (Chapter 2 — the
  investigation-map we're building toward): `WORLD_DESIGN.md`.

This file plus `README.md` are the orientation — open only the files you're about to
change rather than re-reading the whole tree. `ROADMAP.md` is the direction; `WORLD_DESIGN.md`
is the current chapter's mechanics.

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

**Next action (pick this up):** Chapter-2 **deception is built and measured** (`hta/ch2/`, run
`python run_slice.py`; `WORLD_DESIGN.md` → "Second slice"). The cycle family member + hidden
boundaries + decoy maps **fixed the transparency problem** (vanilla Haiku now sits ~0.40–0.60
of the band, no longer pinned at the oracle) and **bet 2 still holds** (R²=1.0). But **bet 1
still fails on aggregate** (taste −0.066 raw, repeats=3) for a new, understood reason: the taste
gap's sign tracks **value-spread** — the hand prompt beats vanilla where value is distributed
across confirm-requiring segments (`decoy`: +0.26 normalized, the existence proof) but *loses*
where a single fat `const` dominates and vanilla banks it cheaply (`mirage`/`tight`). The
concrete next build (deliberate, **not** a map grid-search toward a PASS): (1) design
**distributed-value** worlds — no single trivially-bankable segment; (2) make the taste prompt
**budget-aware** (bank long runs cheaply, reserve confirm-probes for ambiguous arith/cycle
only); (3) re-measure once, then build the loop iff a careful hand prompt beats vanilla robustly
— else the **judge/difficulty** needs the rethink. `ROADMAP.md` → "Chapter 2" is the arc; the
bash below still runs Chapter 1.


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

## The two invariants (the integrity floor — they survive every chapter)

- **Objective, agent-inaccessible scoring** — worlds are scored by a **dumb deterministic
  function**, never an LLM judge (the agent is optimized *against* the score, so a movable
  score is reward-hacking). *Ch1:* empirical equivalence on a fixed battery — pure
  `f(x,y,z) → bool` (`hta/world/engine.py`). *Ch2:* information-weighted **coverage** via
  **DP on a fixed graph** (`WORLD_DESIGN.md`). The world stays **deterministic** so optimal
  play (the oracle) is computable.
- **Safe-eval** — model output never executes. *Ch1:* every rule string is AST-validated
  against a strict whitelist and `eval`'d with no builtins (`hta/world/grammar.py`). *Ch2:*
  the smith proposes a **validated declarative spec** that our deterministic expander
  realizes — same principle, lifted from rule-lambdas to grammar-specs.

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
- **Answers (implementation mode; for design/strategy see "Voice & altitude"):** lead with
  the verdict (do/skip + the action), back claims with `file:line`, recommend rather than
  offload the decision, keep caveats short and last, and don't frontload detail that wasn't
  asked for — expand on request.

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
