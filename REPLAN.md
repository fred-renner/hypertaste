# REPLAN — the Pass-3 rewind (proposals for the PI brainstorm; nothing here is locked)

Drafted 2026-06-10 from the live PI conversation. Status: **agenda + recommendations for the
redo of the Pass-3 brainstorm** — the session PLAN.md always scheduled and the previous
session ran solo. Every item below is a proposal until ratified. Process line, adopted now:
**steps marked "brainstorm" are PI sessions, never executed solo.**

## The finding that forces the rewind

The hidden-map world violates the project's own threshold gate (ROADMAP → "earning its
keep"): the candidate lattice is public and the hypothesis family enumerable, so the optimal
policy is articulable — "enumerate the consistent shapes, probe where they disagree, deepest
first" fits on a napkin. Below that line a hand spec is competitive and a measured taste-gap
is noise. The world trained menu-reading, not inquiry: real research has no menu.

Root cause, named precisely: **the exact best-play oracle was never the invariant — it was an
implementation choice wearing the invariant's clothes.** The constitution requires scoring
that is mechanical, deterministic, agent-inaccessible. It does not require a public,
enumerable hypothesis family. That choice is the single root of the public lattice, the
4096-hypothesis richness cap, the ratchety grammar-extension growth, and the proxy
unfaithfulness the 2026-06-09 live run already surfaced.

## Proposal 1 — the world: planted systems, scored by held-out prediction

The lab generates a hidden system from a rich compositional grammar (the agent never sees
the grammar): small interacting components — function networks, state machines, processes —
wired by a seeded RNG. The agent probes it (input → output) under a scarce budget, keeps any
notes it likes, and is scored on **predicting the system's behavior on lab-chosen held-out
probes**, structure-weighted, normalized as **skill above the base-rate guesser** (lazy
constant predictions earn exactly zero — the fix Chapter 1's agreement-blend lacked).

- The constitution holds: scoring is a dumb comparison against planted ground truth.
- From the inside the hypothesis space is open: no menu, no enumeration move; theories are
  formed and bet on under genuine uncertainty — the actual shape of empirical science, as
  close as a gym can get while ground truth stays plantable (the non-negotiable).
- The threshold gate passes by construction: Opus cannot write the optimal policy on paper
  for an open hypothesis space.
- Cost: the build side gets cheaper (no oracle enumeration at all — scoring is run-and-
  compare; generator + screen are stdlib, model-free, free). Live episodes stay cents.
- The smith's native move becomes mutation over the generator grammar (compose two systems,
  deepen one, couple their state) — continuous difficulty, no grammar-as-code-event ratchet.
- Multi-horizon/coupling survive as world properties: coupled components mean you must hold
  a theory of one to design informative probes for another. Multi-goal later = multiple
  output ports with different payoffs. Measured, never installed.

## Proposal 2 — the ship-gate goes empirical (the live run already said it must)

- **Hard:** a battery of frozen generic probers (random, sweep, bisect) scores ~zero skill.
- **Solvable:** a mechanical information-sufficiency certificate — the lab, knowing what it
  planted, verifies a probe schedule within budget whose answers pin enough structure to
  predict well. (Kept mechanical; no hand-written reference policies as the answer key —
  that was the unfaithful-proxy trap. Whether the live student can do it is what live
  calibration and the ZPD check are for.)
- **ZPD:** the live champion fails where a coached fix succeeds — the only coupling that was
  ever faithful.

## Proposal 3 — the baseline battery (the null, made measurable, day one)

The standing worry "what if a basic tasteful-researcher role prompt gets you there" is not a
threat to the project — it IS the null hypothesis, and it becomes row one of the battery:

1. vanilla weak player;
2. weak player + one-line "be a tasteful researcher" role prompt;
3. **the smart-spec null:** the best hand-written playbook PI + Opus can produce on day one,
   then frozen.

Paired seeds, same worlds, skill scores. If (2) or (3) matches the grown champion
indefinitely, the harness is not earning its keep and the instrument said so honestly —
which only this apparatus can find out. Relative, paired, empirical measurement is enough
because the question is comparative; "distance from perfect play" never answered it.

## Proposal 4 — unlock, never install (the thesis, self-applied)

- **Hard length cap on the playbook** (plus the MDL prior within the cap). A capped playbook
  cannot accrete situation-specific rules; every edit becomes a trade — to add a principle
  the coach must compress or delete one. This is the structural fix for the observed coach
  failure (the hedge: precise diagnosis, regressive *addition*). A grown artifact that
  compresses is judgment; one that lists is a lookup table — the PI's red-flag instinct,
  formalized.
- **The body does bookkeeping, never choosing.** Ledgers, summaries, scratchpads — yes:
  they free the weak player's working memory so native judgment isn't drowned in
  arithmetic (maximizing native capability). The allocator — when to switch goals, chase an
  anomaly, commit — must stay in the grown procedure: wiring it into the harness would make
  us the smart-spec null. The world makes the move *necessary*, the body makes it
  *possible*, the procedure learns *when to fire it*.
- **Affordance limits go through the ratified ring:** when run evidence says the bottleneck
  is the body, the loop proposes, the PI applies. Run artifacts must make affordance-limit
  evidence legible.

## The two ratchets (reconciliation)

Discrete *difficulty* jumps in the curriculum are fine and human-like — taste grows in
stages. The smell was the other ratchet: each new world axis a hand-coded event, the
codebase accreting special cases of one bespoke world. A compositional generator dissolves
the second while keeping the first.

## What survives from PLAN.md, what is superseded

Survives: the three rings, the pass discipline with free offline gates, Passes 0–2 as
landed, the situations instrument, the port check, the coach quality-control of Pass 5
(now natively mutation-based), Pass 6 multi-goal, Passes 7–8.

Superseded: the Pass-3 design record (the hidden-map world — demoted to an offline
regression fixture: refactor on it, don't invest in it); design lock 4's oracle band
(replaced by the empirical band above); design lock 1's "family public and enumerable"
framing where it conflicts with the open hypothesis space.

## Open questions for the brainstorm

1. Generator grammar v1: which component classes (function networks? state machines?
   processes?) and which composition operators give rich shapes with cheap planting?
2. The held-out set: how the lab structure-weights it mechanically; how to keep prediction
   elicitation lean (probe format, K questions, proper scoring rule).
3. The budget shape: probe costs uniform or heterogeneous (cost discovery is itself a taste
   axis — later?).
4. Where situations plug in: a constructed mid-state is now "partial theory + remaining
   budget" — what is the minimal faithful encoding?
5. The smith's mutation operator set v1, and what the no-op/control mutations are.
6. The playbook cap: what length, and does the cap bind the seed too?
7. RSI scope: whether the loop runs long or short is an empirical output of the curve, not a
   commitment — what saturation evidence would close a chapter?
