# World research — which existing benchmarks best test the taste thesis

> Survey of off-the-shelf benchmarks/worlds, read against `THEORY.md` (the abstract spec), not
> just `BET.md`'s single-world pick. Verdict: **no single world tests the thesis** — THEORY.md's
> transfer claim is cross-domain, so the target is a small **battery**, not one arena.

## What THEORY.md demands of a test world

The thesis fixes the type signature — taste is *the value function of a search with no reward
signal* — and that forces a checklist. Six demands; the last two are what THEORY.md adds over
BET.md's DiscoveryWorld pick:

1. **No gradient, value un-guessable without playing.** If the best move reads off the rules it's
   calculation, not taste. (Kills static QA and most "reasoning" sets.)
2. **A path, not a hop** — goal many linked moves away, each unlocking the next, with stepping
   stones. (Kills single-answer tasks.)
3. **Mechanical, agent-inaccessible scoring, and reality pushes back mid-episode** — the integrity
   floor plus the forecast-act-revise loop need the *world*, not a judge, to return the truth.
4. **Memorization-resistant** — held-out by construction, or "every agent trained on it" bites.
5. **Scalar = compression discounted by compute** (§1), exercising more than one of the five axes:
   not just compression and learning-progress but **generativity** (does this position open many
   others) and the recursive **apparatus-upgrade / ontology revision** (does good play require
   inventing a new vocabulary).
6. **Multi-domain.** The big addition. §2–§3: the portable part — the invariant-sensor — *only
   self-assembles when the stream spans domains*; a single world can't test transfer at all.

## The landscape, scored

| World | No-gradient / un-guessable | Path (compounding) | Mechanical + pushes back | Memo-resistant | Scalar / axes hit | Multi-domain | Drivable by cheap LLM |
|---|---|---|---|---|---|---|---|
| **DiscoveryWorld** (Ai2 '24) | ✓ | ✓ | ✓ (path-score *built in*) | ✓ (parametric) | compression+LP; weak depth/ontology | ✓ (8 fields) | ✓ text+API |
| **NewtonBench** (HKUST '25) | ✓✓ | ✓ | ✓ (interactive probing) | ✓✓ (law shifts) | **compression/MDL direct** | ✓✓ (12 physics) | ✓ |
| **DM Alchemy** ('21) | ✓✓ (infer latent) | ✓ | ✓ | ✓✓ (resampled/ep) | ontology+LP+empower | ✗ (one domain) | ✗ (3D Unity RL) |
| **Zendo / active-rule** ('24) | ✓ | ✗ (short) | ✓ | ✓ | **boundary-seeking** | ✗ | ✓ |
| **RULEARN** ('24) | ✓ | ~ | ✓ | ✓ | abduction/LP | ~ (3 types) | ✓ |
| **Baba Is AI / Keke** ('24) | ✓ | ✓ | ✓ | ✓ | **ontology revision (axis 5)** | ✗ | ~ (floor risk) |
| **Crafter / Craftax** ('24) | ~ (tech-tree calculable) | ✓✓ | ✓ | ~ | **generativity/empowerment** | ✗ | ~ |
| **ARC-AGI-1/2** ('25) | ✓ (pure abstraction) | ✗ (one hop) | ✗ (QA, answer-scored) | ✓ | compression (axis 5) | ✗ | ✓ |
| **RE-Bench / MLE-bench / PaperBench** | ✓ | ✓ | ✓ | ~ | high taste — but **code** | ~ | ✗ ($$, code) |

## Recommendation: a three-world spine + axis-microscopes

**Spine:**

1. **Keep DiscoveryWorld.** The only candidate that scores the *path* directly (its
   "task-relevant-actions" metric is a mechanical path-score, dissolving path-vs-answer) and pushes
   back mid-episode. The drivable spine.
2. **Add NewtonBench** — the strongest THEORY.md-*native* addition, post-dating BET.md. Almost
   literally §1: the win is recovering a *compact hidden law*, so the score tracks the MDL scalar,
   not a proxy. Counterfactual law shifts make answers un-guessable by construction (cleanest pass
   on demand 4); interactive model-discovery (3); 12 domains (6). The gift: its headline finding is
   that a code interpreter *hurts* strong models by inducing a premature exploration→exploitation
   shift — they **satisfice**. That is our core failure mode (the missing discriminating-move habit)
   already isolated and measured. A ready-made arena for the toggle.
3. **Hold Alchemy in reserve** — the purest instantiation of the type signature (latent causal
   structure resampled each episode, *no* reward, solvable only by hypothesis-testing). But it's
   3D-Unity RL, not LLM-native; the adapter cost makes it a v2 stretch, not a v1 pick.

**Microscopes** — each stresses one axis the spine is weak on; probe a single guard, don't replace
the arena:

- **Zendo / active-causal-discovery** — the *discriminating-move* guard (demand 5's
  boundary-seeking): "design the experiment that splits your hypotheses" in miniature, with a
  Bayesian-OED oracle to borrow as ground truth.
- **Baba Is AI** — the *apparatus-upgrade* axis (§2 axis 5): the rare *playable, path-scored* world
  where winning requires manipulating the rules themselves (revising the ontology). The one axis
  DiscoveryWorld and NewtonBench can't exercise.
- **Crafter / Craftax** — the *generativity/empowerment* axis: open-ended tech-tree where a
  position's worth is how many futures it opens.

## The honest gap

THEORY.md's two most distinctive claims resist a world that also passes demands 2–3:

- **Axis 5 (ontology revision) and true logical depth** live in abstraction worlds (ARC, Baba) —
  but those are one-hop and answer-scored, breaking "path" and "reality pushes back." Genuine
  tension: *the most taste-laden axis is the one that resists path-scoring.* DiscoveryWorld +
  NewtonBench buy compression + learning-progress + a little generativity; they do **not** buy the
  recursive axis. Decide up front whether v1 brackets it (recommended) or pays Baba's floor risk.
- **The transfer claim (§3) needs cross-domain wiring made explicit.** BET.md measures lift on
  held-out *variations within one world*; THEORY.md says that's too weak. Cheapest faithful upgrade:
  train the read on DiscoveryWorld, measure its port to NewtonBench (or across DiscoveryWorld's 8
  fields as a weaker proxy). That's the only setup that tests §3's "the estimator doesn't transfer,
  the infrastructure does" — a small delta on the existing plan.

**Bottom line:** DiscoveryWorld stays the spine; **NewtonBench is the highest-value addition** (it
tests the MDL scalar and un-guessability better than DiscoveryWorld and hands you the failure mode
pre-measured); Alchemy is the purest-but-expensive reserve; and the real shift THEORY.md forces
over BET.md is to treat the target as a *cross-domain battery with a transfer measurement*, not a
single arena.

## Sources

- DiscoveryWorld — https://openreview.net/forum?id=cDYqckEt6d · https://allenai.org/blog/evaluating-scientific-discovery-agents
- NewtonBench — https://arxiv.org/abs/2510.07172 · https://huggingface.co/papers/2510.07172
- DeepMind Alchemy — https://arxiv.org/abs/2102.02926 · https://github.com/google-deepmind/dm_alchemy
- Zendo / "Doing Experiments and Revising Rules" — https://arxiv.org/pdf/2402.06025
- RULEARN + IDEA — https://arxiv.org/abs/2408.10455
- Baba Is AI — https://arxiv.org/abs/2407.13729 · Keke AI Competition — http://keke-ai-competition.com/
- Craftax — https://huggingface.co/papers/2402.16801
- ARC-AGI 2025 review — https://lewish.io/posts/arc-agi-2025-research-review
- Goal-Oriented Bayesian Experimental Design — https://arxiv.org/abs/2507.07359
