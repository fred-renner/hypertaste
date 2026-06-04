# World design — how the world grows

How the world evolves beyond classic numeric WILT so that *research taste* keeps being
the thing that wins, without breaking objective scoring or the airgap. Grounded in the
current code; cites the files each change touches.

Axes A (compositional worlds) and B (sampled hypothesis space) are implemented; the
scorer (`score_guess`) and the AST airgap (`validate_lambda`/`compile_rule`) are
unchanged. Everything under "Explicitly deferred" remains deferred.

## The constraint that picks the axis

Two invariants make `hypertaste` work, and any growth axis has to keep both:

1. **Objective scoring.** A world scores a guess by *empirical equivalence*: the
   guessed lambda equals the hidden rule iff they agree on a fixed deterministic
   battery (`hta/world/engine.py` → `WiltWorld.score_guess`, `_BATTERY` ≈ 729
   structured + 120 random triples). This works for **any deterministic, pure
   function `f(x,y,z) → bool`** and nothing else: the moment the rule has hidden
   state, history-dependence, or randomness, "agree on a fixed battery of inputs"
   stops being well-defined.
2. **Airgap.** Every rule — seed, world-smith output, agent guess — is AST-validated
   against a strict whitelist and `eval`'d with no builtins (`hta/world/grammar.py` →
   `validate_lambda` / `compile_rule`). Model-generated rule strings can't execute
   arbitrary code.

So the cheapest, safest growth is whatever stays a **pure deterministic boolean
function of the triple** — it inherits the scorer and the airgap *for free*. The
expensive growth is whatever breaks invariant (1).

Scoring the candidate axes against that:

| Axis | Stays pure `f(x,y,z)→bool`? | Scorer change | Airgap change | Verdict |
|---|---|---|---|---|
| **Compositional / multi-rule** (regimes, exceptions, conjunctions) | **Yes** | none | none | **PICK — Axis A** |
| Generative hypothesis space (decouple library) | n/a (metric, not world) | info-gain only | none | **PICK — Axis B (enabler)** |
| Wider rules (N>3 vars, sequences) | yes-ish | battery + channel arity | grammar arity bump | defer (orthogonal, layer later) |
| Latent state / multi-step / history-dependent | **no** | rebuild scorer | new probe protocol | defer (breaks invariant 1) |
| Noise / stochastic labels | **no** | likelihood-based scorer + novelty rethink | none | defer (breaks invariant 1) |
| "Real research" worlds (rule = program/dataset/sim) | no | bespoke scorer | sandbox | defer (long-term target) |

## Recommendation: implement Axis A + Axis B first

### Axis A — Compositional / multi-rule worlds

**Why this one.** The grammar *already* admits everything compositional rules need —
`and` / `or` / `not`, all comparisons, `IfExp` (ternary), `abs/min/max`, full
arithmetic (`hta/world/grammar.py:_ALLOWED_NODES`). So **regimes, exceptions, and
conjunctions are already expressible and already safe to compile**; we are not
expanding the attack surface at all. Yet the current library is dominated by
*atomic* rules (one comparison, one arithmetic relation). Compositional rules are
exactly where research taste pays off:

- **Regimes** — `lambda x,y,z: (x<y<z) if x<0 else (x>y>z)` — reward *hypothesis
  decomposition*: you have to notice the world behaves differently in two regions.
- **Exceptions** — `lambda x,y,z: x<y<z and not (z-x==4)` (already in the library as
  `inc_not_const`, our only difficulty-5 rule) — reward *falsification*: the rule
  looks like plain "increasing" until you probe the carved-out hole. Confirm-only
  probing never finds it.
- **Conjunctions / disjunctions** — `(x<y<z) and (x+y+z>0)` — reward composing two
  partial hypotheses instead of pattern-matching one.

This is the most direct lever on the project's actual goal, it's the cheapest
(scorer + airgap untouched), and TODO 1 already showed the meta agent independently
inventing a *falsification-first probe battery* — exactly the taste these worlds
exercise. We give that taste something to bite on.

**What changes (code):**
- `hta/world/world_smith.py:_SMITH_PROMPT` — instruct the smith to compose rules
  (regime/exception/conjunction templates), and to report a `structure` field
  (`atomic` | `conjunction` | `regime` | `exception`) alongside `difficulty`/`tags`.
- `hta/world/grammar.py:_RAW_CANDIDATES` — add ~6–8 compositional seed rules so the
  library fallback (and the offline mock inductor) can still cover the harder
  curriculum. Add a `structure` field to `RuleSpec` (parallel to `tags`).
- **Solvability gate** (new, small helper in `world_smith` or `grammar`): reject a
  generated rule unless, on `_BATTERY`, it is **non-degenerate** — produces *both*
  True and False with neither outcome below ~5% (kills constant-True/False and
  near-trivial rules) — and **solvable-in-principle** (a reference Occam inductor with
  a generous probe budget recovers it). This is the concrete ZPD-floor: it stops the
  smith handing the agent unsolvable or degenerate worlds.

**Scorer change: none.** `score_guess` already enumerates the battery; a compositional
rule is just another `f(x,y,z)`.

### Axis B — Generative / sampled hypothesis space (required enabler for A)

**Why it's coupled to A.** The info-gain metric — `w_info` = 0.15 of fitness — is
measured as *candidate-library reduction*: `hypothesis_reduction` (engine) counts how
the agent's probes shrink the **25-rule `candidate_library()`** (`hta/world/grammar.py`).
That library currently doubles as both the measurable hypothesis space *and* the
smith's fallback. The instant Axis A produces rules outside those 25 templates, the
library no longer contains the true rule, so `consistent_candidates` can collapse to
the wrong set (or empty), and `avg_info_gain` reports noise. This is the core info-gain
scaling problem: how does the metric behave when the library no longer covers the rule
space? We must decouple them before A is meaningful.

**The fix — version space over a sampled rule set.** Replace "hypothesis space = the
fixed 25 library rules" with "hypothesis space = K rules **sampled from the grammar**"
(including compositional structures), seeded deterministically per world so the metric
stays reproducible. `hypothesis_reduction` then measures version-space collapse over
that sampled set — purely a function of the hidden rule + the probes, no dependence on
whether the true rule happens to be one of 25 hand-written templates. The candidate
library stays, but demoted to its honest roles: a **prior/seed** for the smith fallback
and the substrate for the offline Occam inductor (`simplest_consistent`) — not the
definition of the hypothesis space.

**What changes (code):**
- `hta/world/grammar.py` — add a `sample_hypotheses(seed, k, max_structure)` generator
  that draws valid (AST-checked) rules from the grammar, biased to the curriculum's
  structure mix. Reuse `validate_lambda` so sampled rules are safe by construction.
- `hta/world/engine.py:hypothesis_reduction` — take the sampled set instead of
  `candidate_library()`; everything downstream (`consistent_candidates`, the
  `avg_info_gain` math) is unchanged.
- `hta/taste.py` — no change to the fitness formula; `avg_info_gain` just becomes
  trustworthy on compositional worlds.

## Design decisions

- **ZPD calibration + avoiding unsolvable / degenerate worlds.** The solvability gate
  (Axis A) is the floor (non-degenerate + recoverable-in-principle); the
  `_target_difficulty` escalator (`hta/loop.py`, escalate at ≥75% solved) is the ceiling.
  `structure` is a difficulty axis the smith climbs (atomic → conjunction → regime →
  exception) rather than just nudging an integer 1–5.
- **World novelty / anti-degeneracy across generations.** Kept objective: a world's
  *behavior vector* is its label over `_BATTERY`. A generated world is rejected when its
  behavior vector is within a small Hamming distance of any world already used this run
  (and of the transfer set) — a model-free measure of "new world vs. relabeled duplicate."
- **Anti-collusion as the smith gets more powerful.** Transfer is an independently
  sampled held-out distribution: drawn from the same grammar with a fixed, separate seed
  (`_TRANSFER_SEED`) and never conditioned on the agent's `weak_tags` (training worlds
  are; transfer is not). That keeps it a genuine held-out distribution, not a fixed list
  the agent could memorize across runs.
- **Where LLM-judged "interestingness" belongs.** World generation only — the smith may
  rank or filter its own candidates. It never enters fitness: `hta/taste.py` is
  deliberately objective because the agent is optimized against that number and an LLM
  judge there is gameable. Interestingness shapes *what worlds exist*, never *what score
  an agent gets*.

## Explicitly deferred (and why, so the next session doesn't relitigate)

- **Stochastic / probabilistic rules.** Highest "real research" payoff but breaks
  invariant (1): no exact lambda exists, so `score_guess` needs a likelihood/Bayes
  scorer, and the novelty metric's core assumption ("no value in repeating a probe",
  `hta/taste.py`) inverts — repeating a probe *is* informative under noise. A whole
  scorer + metric redesign; do it as its own focused axis after A+B land.
- **Latent state / multi-step / history-dependent rules.** Breaks invariant (1) the same
  way (the "input" becomes a sequence; the fixed-battery equivalence test no longer
  defines correctness) and needs a new probe protocol on the channel.
- **N>3 variables / sequences.** Orthogonal and layer-able later; needs a grammar arity
  bump, a battery rebuild, and channel-arity changes, but doesn't conflict with A+B.
- **"Solve the world" program/dataset/simulation worlds.** The long-term target; out of
  scope for the first 1–2 axes.

## Suggested first slice (smallest shippable)

1. Add `structure` to `RuleSpec`; add ~6–8 compositional seed rules to the library.
2. Add the **non-degeneracy + solvability gate** in `world_smith.build_worlds`.
3. Add `grammar.sample_hypotheses(...)` and switch `engine.hypothesis_reduction` to it.
4. Update `_SMITH_PROMPT` to compose rules and emit `structure`.
5. Add the **behavior-vector novelty** reject and the **independently-seeded transfer**
   distribution.
6. Extend tests: a compositional rule round-trips (validate → compile → score), the
   solvability gate rejects a constant rule, info-gain is non-zero on a compositional
   world, and two near-duplicate worlds are de-duped.

All six keep the scorer and airgap byte-for-byte where they are — the whole point of
picking A+B first.
