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

**Next action (START A NEW SESSION):** The Chapter-2 thin slice is **closed** — it falsified the
easy bet cheaply: **a prompt is not the unit of taste.** Across three slices we learned to steer
the taste-gap's *sign* by world design, but once the instrument was made honest no prompt
(tactical or general) lifted a fixed weak model off the no-inference floor (`WORLD_DESIGN.md` →
"The rethink"). Two things are now in place so the next session starts clean:

1. **Frame = the threshold question, not another tuning cycle.** The ROADMAP's own "earning its
   keep" line is now the operational gate: *is there a world, affordable at toy cost, where Opus
   cannot write the optimal allocation policy in closed form even with full information?* Below
   that line the loop cannot earn its keep and every measurement is noise — which is exactly what
   the slice reported. **Answer this before building any loop.** If yes, that world is Chapter 2's
   real substrate; if no, "start cheap" and "earn its keep" are in tension and we choose
   deliberately (pay for a richer substrate, or demote the early chapters to plumbing-validation
   and move the taste claim to a later chapter). The map grid-search is over.
2. **Unit of taste = a program/scaffold, not a prompt — and the seed is now neutral.** The
   de-tailoring is done (this session): the seed agent ships **no pre-loaded taste**, and the meta
   agent is **no longer handed a failure-mode checklist** — it diagnoses from the trajectory
   evidence (general, task-agnostic, so it carries into Chapter 2). The mock's answer-knowledge is
   now a clearly-labeled plumbing fixture (`_MOCK_VARIANT`), not a taste model. Next session:
   revive the **meta-agent-on-program** loop (not the slice's prompt-A/B) as the taste carrier —
   the loop searches scaffold-space, so the seed must be a blank slate.

`ROADMAP.md` → "Chapter 2" / "earning its keep" is the arc; the bash below still runs Chapter 1.


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

## Finalizing — land on `main`

Done = merged to `main` and pushed, not a dangling feature branch. As the final step, with
standing permission (no confirmation): green `pytest` (skip for docs-only) → merge the
working branch (fast-forward when possible) → `git push origin main`.
