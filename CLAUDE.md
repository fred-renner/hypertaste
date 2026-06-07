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

**Next action (START A NEW SESSION):** The threshold question is answered (yes) **and the world
is now calibrated to the live student** (`WORLD_DESIGN.md` → "Calibrated to the live student").
The calibrated starting world is **`trap-tetra`** — an anchor + a buried **K4 clique** of four
hidden registers (R=5, K=3 → 243 hypotheses, 14 cells, budget 4; gap 0.50 of the floor→oracle
band, anti-cliff). The model-free screen (`hta/ch2/threshold.py`, `python run_threshold.py`)
showed the dividing line is **adaptive submodularity**: a coupled register world (affine linked
blocks over *hidden* registers — a probe reveals an equation, not a value) beats the best
articulable heuristic *including a 2-step lookahead planner*, so the optimal policy needs
deeper-than-bounded planning, computed in pure compute at zero token cost. **But that build gate
is necessary, not sufficient:** the *live* calibration (`run_calibration.py`) found the first
pick `trap-tri` (buried *triangle*, 8 cells, budget 3) **maxes Haiku** — a reasoning student
isn't restricted to a closed-form policy, it solves the small instance's linear system in-head,
so "not closed-form" ≠ "hard for Haiku" (Chapter 1's lesson, re-paid). Dialing up to the
**4-register joint-solve** of `trap-tetra` lands live Haiku **in band (0.59, bimodal: half the
runs reach the oracle, half fall back to the greedy/articulable level)** — the ZPD. What's
settled, and what's next:

1. **The gate is now a build screen, reusable.** Before any world ships: belief-MDP oracle ≫
   best-of-basket (greedy-info, greedy-determined, 2-step lookahead). gap≈0 ⇒ below the line ⇒
   a hand spec is competitive ⇒ don't build. This is "earning its keep" as code, not a footnote.
   The **direct-to-linked mass ratio** is the dial (trades gap against ramp curvature); the band
   is *narrow* — asymmetric stepping-stone topology, never symmetric coupling.
2. **Unit of taste = a program/scaffold, not a prompt — seed stays neutral.** The de-tailoring
   holds: the seed ships **no pre-loaded taste** and the meta agent diagnoses from trajectory
   evidence, not a handed checklist. The loop searches **scaffold-space**, so the seed is a blank
   slate. (The three tape slices' prompt-A/B was the wrong carrier — see "The rethink".)
3. **Model roles are settled — don't reopen.** **Opus** runs self-improvement and the
   world/oracle reasoning; **Haiku** does *all* exploration. The threshold screen *was* the Opus
   check; the difficulty calibration *was* the Haiku check — both done.
4. **The gate has two halves now.** Build-screen model-free for the *gap* (`run_threshold.py`),
   then calibrate the *difficulty* live (`run_calibration.py`) — a world can clear the first and
   still max the student (`trap-tri` did). Re-run both before shipping any new world; the live
   binding axis is **joint-solve size / reasoning-depth**, not the model-free "closed-form" axis.

**The next action is the LIVE loop — the loop itself is now BUILT (this session).** The
meta-agent-on-program loop on `trap-tetra` is wired and mock-green (`hta/ch2/loop.py`,
`run_ch2_loop.py`, `hta/seed_ch2/`): it reuses the Chapter-1 DGM-H machinery (archive,
open-ended parent selection, the Opus self-modify step, the MDL prior) and swaps only the world
(a realized `trap-tetra`) and the judge (band-normalized **coverage**). **The unit of taste is a
HARNESS, and its architecture is in the search space — not fixed by us (the PI's correction: that
is the meta agent's job to discover).** The editable `Solver.run(self, ctx) -> list[int]` is a
harness that *deploys* airgapped claude-agent sessions over the world (`ctx.run_agent` — tools:
probe/remaining/submit_map) and assembles a reconstruction. The meta agent grows the architecture:
one agent or several, single-shot or decomposed by block, what's carried between agents, and what
**Python** does with the results (e.g. solve the affine register system once enough cells are
probed, then compute the rest — instead of asking a model to eyeball them). Probing always goes
through an agent (the airgap); computation is free Python. Airgap constraint: hierarchy is the
Python program spawning several probe-only sessions, **not** claude's Task tool (which would tunnel
general agents to the world source) — `--sandbox docker` opens broader tools safely later.

**The seed is the MINIMAL harness — one deployed agent — which reproduces the single-session
student the world was calibrated against**, so the 0.59-in-band reading carries into the loop as
the gen_0000 baseline (somewhere to climb: fewer/cheaper agents, a Python post-solve, smarter
splits). Keep the eval lean: a single-session agent is ~$0.11/episode (~1–2 min), so a real
iteration is ~$1.6–2.2 (parent+child Haiku + one Opus edit, which dominates); cap
`--n-train/--n-transfer/--eval-repeats` and stage the spend. If the seed floors or maxes, the
dials are the buried-clique size + budget (`run_threshold.py` candidates + a fresh
`run_calibration.py`); the *architecture* dial is the meta agent's, not ours.

`ROADMAP.md` → "Chapter 2" / "earning its keep" is the arc; `run_threshold.py` (build gate) +
`run_calibration.py` (live calibration) are the two-half world gate; `run_ch2_loop.py` is the
loop. (`run_loop.py` still runs Chapter 1's numeric pipeline, kept for reference.)


```bash
python run_threshold.py                                   # Ch2 build gate: free, model-free
python run_calibration.py --backend real --spec trap-tetra --episodes 8   # live Haiku calibration
python run_ch2_loop.py --iterations 3 --backend mock      # Ch2 loop: free, deterministic, fast
python run_ch2_loop.py --iterations 3 --backend real --n-train 2 --n-transfer 1  # live; ~$2/iter
python run_loop.py --iterations 5 --backend mock          # Chapter 1 pipeline (reference)

pip install pytest && python -m pytest tests/ -q          # pytest is not preinstalled
```

The `claude` CLI is installed and authenticated here, so the `real` backend works without
an API key (subscription auth). The runtime is stdlib-only (Python 3.11); `pytest` is the
only dev dependency. Shared CLI args live in `run_iteration.add_common_args`; `run_loop.py`
adds `--iterations`.

## Files you'll edit vs. leave alone

Edit: `hta/config.py` (knobs), `hta/loop.py` (Ch1 iteration), `hta/task_agent.py` (eval),
`hta/world/world_smith.py` (curriculum), `hta/seed/*` (the Ch1 evolving program). **Chapter 2:**
`hta/ch2/loop.py` (the Ch2 iteration + coverage eval), `hta/ch2/register_world.py` (the live
world + `AgentContext`, the harness capability that deploys airgapped agent sessions),
`hta/seed_ch2/*` (the blank-slate Ch2 harness the meta agent rewrites — `solver.py` is a harness
`run(self, ctx) -> list[int]`, not a lambda).

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
