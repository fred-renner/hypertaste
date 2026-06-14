# Finding — instance 0 (the "machine"/explorer world): a tactic, not taste (2026-06-14)

A saved record of the first attempt at the proof of principle on the post-`PASS3_REDO` world, the
result, and the honest reading. Kept separate on purpose: the next session is a repo cleanup, and
this is the lab note that should survive it. **Don't treat this as a current design — it's a
post-mortem.**

## What we set out to do

The settled bet (`PASS3_REDO.md`): grow *taste* — *choosing your next move well by evaluating your
position* — and measure it by whether a grown playbook beats the best day-one playbook on fresh
worlds, same weak student, same body. Instance 0 was meant to be the smallest honest slice of that
on the new world (not the retired anchor/trail world).

## What the world is (plainly)

You face a handful of "outputs." Each turns a number you choose (an input) into a number you read.
Each output is secretly one of three simple functions: a **constant**, a **straight line** (a·x+b),
or an **arbitrary lookup table** (a random value per input). You get a small budget of reads; reading
earns nothing. At the end you write your best guess of each output's rule and are scored on inputs
you never read: right rule (or a fully read table) → full marks; "don't know" → a small consolation
credit; wrong guess → zero. The only skill the world rewards is *budget allocation*: tell the cheap
outputs (lines, ~3 reads) from the expensive ones (tables, read-every-input), bet your budget on the
affordable valuable ones, abstain on the rest. The three part types are arbitrary knobs chosen to
manufacture exactly that cheap-vs-expensive tension; they don't stand for anything.

## What we built

- A kit + builder + exam + dumb deterministic scorer + scripted-QA gate (all free, model-free).
- A confined episode body (probe / read-map / scratchpad / submit) behind a stdio-MCP airgap.
- A **bespoke** author/coach/eval driver — NOT the existing `hta/ch2/loop.py`. One Opus completion
  writes the day-one playbook; one Opus completion rewrites it once from a sanitized conduct report;
  then bare/day-one/coached are evaluated. No archive, no parent selection, no sandboxed agentic
  meta-edit, no iteration.

## The result (two live runs, ~$2.5 each)

| run | draws | bare | day-one | coached | coached − day-one |
|-----|-------|------|---------|---------|-------------------|
| seed 0 | n=5 | 0.144 | 0.172 | 0.198 | +0.025 |
| seed 1 | n=6 | 0.270 | 0.243 | 0.326 | +0.082 |

Coached > day-one both times. The coach grew, in its own words: *"budget to finish, not to survey;
a fully read table is guaranteed weight."* (Full transcripts + playbooks: `runs/instance0/`.)

## The honest reading (the real talk)

1. **Half a habit, not taste.** "Budget to finish, not to survey" *is* general and transferable.
   "A fully read table is guaranteed weight" is a reflex about *this* scoring rule — it dies the
   moment a region returns randomness. We grew one portable clause welded to one world-specific trick.

2. **The habit mirrors the structure you plant.** We planted a budget-allocation puzzle (inherited
   from the anchor chapter), so we grew a budget-allocation tactic. The world has **no structure to
   read**: the outputs are independent, single-knob, one-of-three functions. No map that builds up,
   no region that unlocks another, no dead end to discover and leave, no anomaly that doesn't fit.
   The "position" is trivial, so the only habit that *can* emerge is rubric-allocation. Taste needs a
   position worth evaluating; this world has none. (And note: hand-authoring a structured world is
   itself the **smith's / calibration's** job, not a thing to hand-build — so the flat world was
   doubly off.)

3. **We did not run the real inner loop.** `hta/ch2/loop.py` already implements the DGM-H loop —
   archive, parent selection, a task-agent eval, and a **meta agent that edits the playbook
   agentically inside an airgapped sandbox**, iterated. None of that ran. The "coach" was a single
   plain-text Opus rewrite standing in for one meta pass, and the driver **duplicates** `loop.py`'s
   eval machinery (which is welded to the anchor world). So the demonstration was "one hand-rolled
   coaching pass nudged a noisy score," not "the loop grows taste." The bar for "it worked" — taste
   readable off the playbook as *position → move*, portable, helping on a structurally-different
   held-out — is exactly what the real meta + task loop is for, and we haven't exercised it here.

4. **Repo history pulled the design.** Orienting on the old chapter's code and docs (the trail world,
   coverage, the oracle, "commit to the deepest chain", PLAN.md's records) re-anchored the build to
   *allocation*. `NEXT.md` warned of this — "the docs got contaminated by the very world we wanted to
   plant." The cleanup (next session) is to make the live docs/code the settled definition + rules +
   a clean brief, and the anchor chapter clearly history, so a fresh start isn't dragged back.

## What survives (reusable)

The scaffolding is sound and worth keeping: the loop-shaped plumbing runs end to end on a fresh
world; the scorer is dumb arithmetic with no LLM judge; the evolved artefact is plain text;
"only the exam pays" is enforced; held-out is fresh instances. The two invariants held throughout.
What to throw out: the flat allocation world, the duplicated bespoke driver (fold into one
world-agnostic loop), and the overselling.

## For next time (not a plan — pointers)

- Clean the repo first (settle the live orientation; archive the anchor chapter).
- The world must have a position worth reading — connected, with compounding access, dead ends, and
  instruments — and that structure is the smith's / calibration's job to produce, not hand-design.
- Judge success by reading taste off the playbook in plain English (position → move, portable),
  using the real meta + task loop, not a score bump on noisy draws.
