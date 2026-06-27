# BET_EXEC — the hand-run, ready to execute

> **Next instance: this is the run sheet. Start at Step 0.** The design is settled in
> `BET.md` (why), the taste content is derived from `THEORY.md` (what taste is), and this file
> is the *how*. Everything here is decided — do not re-open the design, do not add machinery.
> The deliverable is **6 episodes and their full traces**, not a verdict.

## What this is

The cheapest test of the whole idea: **does taste, written down as a world-general playbook,
lift a weak agent on a path-scored discovery task?** We hand-run it once — no archive, no
world-smith, no evolutionary loop. Two arms, one mutation (the playbook), measured.

## v1 scope (decided)

- **The evaluator slice only** — choosing well among moves already in front of you. THEORY's
  axis 5 (inventing the representation / setting the apex goal — the generator) is **out of
  scope**, deferred. A v1 lift is evidence that taste-as-*evaluator* ports onto a weak model,
  and nothing more. Do not let a v1 win be sold as the whole theory.
- The apex goal is **supplied by the world** (the task) — consistent with THEORY ("supply the
  apex as input").

## The arena (decided)

**DiscoveryWorld** (Ai2, NeurIPS 2024) — `https://github.com/allenai/discoveryworld`.

- **Field: rocket science.** (One of the 8 topics; 3 difficulty tiers, parametric variations.)
- **The taste metric is the procedural report-card** — DiscoveryWorld's middle metric (the
  fine-grained score of *task-relevant actions taken*). THEORY says taste lives at the
  boundary — the discriminating move that splits hypotheses — and that is what the report-card
  measures. **This is the primary outcome.** Binary task-completion and explanatory-knowledge
  accuracy are collected too, but they score the *answer*, not the path — secondary.

## The two arms (decided)

Same Haiku subagent, same action interface, same model, same task variations. **The only
difference is the prompt fed in:**

- **Taste arm** → `playbook_taste.md` (the forecast→act→revise loop + the two guards).
- **Baseline arm** → `playbook_baseline.md` (a competent generic researcher, no allocator
  discipline). It is a *fair* baseline, not a strawman — same framing minus the taste content.

The playbook is **world-general** — it never names DiscoveryWorld or rocket science. The
instant it is tuned to the task, we are measuring overfitting, not taste. Do not edit it to
chase a result.

## The realization — subagents, not a harness

The Agent tool **is** the plumbing. No `hta/llm.py`, no custom scaffold.

- **One Haiku subagent = one episode.** Spawn it with `model: haiku`, give it the arm's
  playbook as its instructions plus the task goal, and let it drive DiscoveryWorld to
  completion over many turns through a confined Bash interface. Haiku because the whole thesis
  is that taste-as-text ports onto a *weak* model — a strong model may already have the reading
  and hide the lift.
- **Opus (the orchestrator) only spawns, collects, and tabulates.** It never plays.
- This is BET's "hold the harness fixed, toggle the allocator" for free: both arms are the
  same subagent + same interface; only the prompt differs.

## The confined action interface (the airgap)

The subagent acts **only** through a thin Bash-callable wrapper around DiscoveryWorld's agent
API — it never reads the simulator source or the task solution. Shape (the next instance picks
exact names):

- `dw_reset --task rocket --tier <N> --variation <V> --run <id>` → returns the opening
  observation; starts/persists an episode keyed by `<id>`.
- `dw_step --run <id> --action "<action>"` → applies the action, returns the new observation;
  loads and re-saves the persisted episode state each call (DiscoveryWorld episode state must
  survive between Bash calls — long-running process, or serialize to disk per `run-id`).
- `dw_score --run <id>` → returns all three metrics, with the report-card's per-item
  breakdown.

The airgap here is **soft and low-stakes** (parametric variations mean reading the source
would not hand over the answer) — but keep it anyway: the subagent's working directory does
not contain the DiscoveryWorld source, and the wrapper exposes only observe / act / score.

## Collect everything

For **every** episode, save to a file the human will read:

- the full action trace (every observation and action),
- the agent's own **forecasts and notes** (the `expect/opens/cost` lines and revisions — this
  is where you see whether the taste arm reasons differently or just got lucky),
- **all three** DiscoveryWorld metrics, including the report-card's per-item breakdown.

The three numbers are the summary; the traces are the evidence. Lay the two arms side by side.

## The run (decided — small, by eye, not statistics)

No pre-registered statistics run. We look at outputs.

- **3 task-variations of rocket science, paired** — the *same* 3 variations played by both
  arms = **6 episodes total**.
- Compare arm-vs-arm on the report-card first, then completion and knowledge accuracy, then
  **read the traces**.
- No win-margin ceremony. We are looking for a visible, legible difference — or its absence.

## Execution steps

- **Step 0 — Stand up the world.** Clone DiscoveryWorld, get it running, confirm a rocket-
  science task loads and the three metrics come back. De-risk BET's "cheap and drivable"
  assumption before anything else.
- **Step 1 — Build the interface.** The `dw_reset / dw_step / dw_score` wrapper above, with
  episode state persisted per `run-id`.
- **Step 2 — Smoke test. STOP here for the human.** One Haiku subagent, taste playbook, one
  rocket task, a handful of actions. Confirm it drives the world and the score comes back.
  Report back before going further — do not run the full set yet.
- **Step 3 — Calibrate the tier.** Plain Haiku (baseline) across the 3 rocket tiers; pick the
  tier where it scores **low-but-nonzero** on the report-card. If the baseline already aces a
  tier, there is no room for lift; if it scores zero everywhere, drop to an easier field as a
  warm-up (ScienceWorld is the fallback, noted in BET).
- **Step 4 — Run.** The 6 episodes (3 paired variations × 2 arms), full traces saved.
- **Step 5 — Tabulate, don't conclude.** Report-card (primary) + completion + accuracy, both
  arms side by side, plus the raw traces. State the numbers and what the traces show. **Do not
  claim "it works."** A null or ambiguous result is a kept result: it means taste does not port
  as static text and the program needs the in-context loop — that redirects the work, it does
  not waste it.

## Discipline — the anti-self-deception rules

- Both arms **identical** except the playbook file.
- The score is DiscoveryWorld's **mechanical** metric — never invent, estimate, or round it in
  our favour. Numbers come from `dw_score`, full stop.
- **Never tune the playbook to rocket science.** World-general or it is overfitting.
- Characters run on **Haiku**; Opus only orchestrates and scores.
- Report numbers + raw traces. The traces are the check on the numbers.

## Explicitly out of scope (do not build)

No archive, no world-smith, no evolutionary / DGM-H loop, no statistics or pre-registration,
no `hta/` machinery. The generator and the capability-discovery / recall world are the v2
target, deferred. v1 is these 6 episodes and a careful look.
