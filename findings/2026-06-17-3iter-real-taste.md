# Finding — three live iterations: the disposition climbs, the score doesn't (yet) (2026-06-17)

First live run of LOOP 1 (grow the agent) on the fresh lab, starting from the Pass-2 build
(`claude/dazzling-franklin-xwgkzm`). Three iterations, real backend, instance 0, `eval_repeats=2`.
$4.15, 36 Haiku episodes + 3 Opus edits. Artifacts: `runs/2026-06-17-3iter-real/`. A lab note, not a
design change — `DESIGN.md` remains the design.

## What we asked

Does **taste** climb over three iterations? "Taste" here is operationalized as band-normalized
**coverage** on instance 0 — how much of the hidden world the agent pins, scored floor→oracle (4→11
raw cells). The agent is fixed-weak Haiku; the only thing that changes between generations is the
English **playbook** Opus rewrites from the trajectory. If taste is real and growable, the playbook
edits should lift coverage iteration over iteration.

## The verdict

**The disposition climbed; the score did not — cleanly — and the score couldn't have told us either
way at this world count.** Two things are true at once:

1. **Opus grew exactly the right move, from trajectories alone.** Never shown the world's structure,
   never told the word "taste," Opus read the conduct and grew the scout-then-commit allocation
   instance 0 plants — and *refined* it across the lineage, ending (gen_0003) on the genuinely deeper
   insight: **reserve the high-yield deep region's budget up front; don't scavenge it from the
   leftovers after grabbing cheap cells.** That is a taste increment you can read directly in the
   artifact (the playbooks in `runs/.../archive/`).

2. **The fitness number did not certify a climb, because draw variance swamps the edit signal.** The
   same seed playbook scored **0.589** on iteration 1's worlds and **0.107** on iteration 2's — a
   swing far larger than the ±0.02–0.22 an edit moves. With only 2 train + 1 held-out world per eval
   (even averaged over 2 repeats), the score is mostly telling us which worlds got drawn, not how
   good the playbook is.

## The data

The honest comparison is **within** an iteration — parent vs. child see the *same* worlds, so it is
fair:

| iter | parent → child | parent | child | Δ (same worlds) |
|------|----------------|-------:|------:|----------------:|
| 1 | gen_0000 → gen_0001 | 0.589 | 0.500 | −0.089 |
| 2 | gen_0000 → gen_0002 | 0.107 | 0.322 | **+0.215** |
| 3 | gen_0002 → gen_0003 | 0.482 | 0.464 | −0.018 |

One of three edits improved the agent on a fair comparison; two were flat-to-slightly-negative. The
loop's own `PROGRESSION` line (children at 0.500 → 0.322 → 0.464) is **not** a taste trajectory: each
iteration reseeds to *different* worlds (`build_worlds`: `base = 10_000*(iter+1)`), so those three
numbers are measured on three different difficulties and cannot be compared. This is the methodology
trap to fix before any climb claim (below).

Held-out (transfer) coverage of the children rose 0.50 → 0.50 → **0.71**, and the best evolved node
(gen_0002) scored 0.482 as a *parent* on fresh iteration-3 draws — well above what the seed scored on
comparably hard draws (0.107). So the lineage did produce a node that generalizes better than the
seed; we just can't certify a monotone climb from three noisy, non-comparable points.

## The lineage (read the playbooks, not the scores)

- **gen_0000** (seed): "spend your budget well; reconstruct as much as you can." Generic.
- **gen_0001**: deferred payoffs are **all-or-nothing** — count the full unlock-cost before the first
  probe; commit only if you can finish the whole sequence; never strand budget halfway.
- **gen_0002**: harvest the immediate-pay clearings first; *the biggest-looking region is the gated
  one — don't let its size pull your early probes*; keep a probed-vs-guessed ledger.
- **gen_0003**: **reverses gen_0002** — do *not* grab the cheap cells first; **reserve** the deep
  region's probes up front and fund it FIRST, then fill leftovers with clearings ("its block of
  probes must be set aside before you start spending, never scavenged from the remainder").

The gen_0002→gen_0003 reversal is the interesting moment: the loop selected gen_0002 as parent (the
weighted open-ended selection correctly compounded onto the better child rather than re-branching the
seed), and Opus then *corrected* gen_0002's "cheap first" heuristic into the capacity-reservation
policy that actually maximizes coverage on a gated valley. The machinery — airgap, lineage selection,
trajectory-only diagnosis — all worked end to end.

## What this changes

Nothing in the design; this is a measurement result. The loop, the airgap, the world language, and
the Opus diagnosis are sound. The bottleneck is **eval signal-to-noise**, and it has two concrete
fixes before the next climb attempt:

1. **More worlds per eval, and a common battery.** Raise `n_train` / `n_transfer` (and keep
   `eval_repeats ≥ 2`) so per-world variance averages down. More importantly, evaluate every node on
   a **fixed held-out battery shared across iterations**, so the progression compares playbooks at
   constant difficulty instead of confounding them with the draw. (Today only parent/child within an
   iteration are comparable; the cross-iteration `PROGRESSION` line invites an invalid read.)
2. **Then re-ask the climb question.** With a common battery, "does taste climb" becomes a clean
   monotone-in-N check on one curve, not three noisy points on three curves.

Cost note: a real episode here was ~$0.08 (Haiku, multi-turn agentic), pricier than the "few cents"
rule of thumb; the 3 Opus edits were $0.48 / $0.29 / $0.39. Raising the world count scales the cheap
episode term, not the Opus term, so a higher-signal rerun is affordable (~2–3× the episode cost).
