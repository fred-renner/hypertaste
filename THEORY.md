# Taste: A Spec (v2)

## 0. Definition

**Taste is the value function of a search with no external reward signal.** It maps the agent's local position to an estimate of positional value — how much good-reachable structure this position connects to — and must commit to a direction *before* the outcome of moving there is observable. Everything else follows from the type signature: a learned `V(position)` trained without labels, because in the regime where taste matters there are none yet.

## 1. The scalar

`V` estimates the quality of the agent's own model, measured as total two-part code length:
```
L = L(model) + L(data | model)        # minimize the sum, not either term
```
Complexity-bits + misfit-bits. A complex model wins iff the fit-bits it saves exceed the complexity-bits it costs; overfit = paying more model-bits than recovered. **Compression ≡ prediction** (Kraft: length `L` ⟺ probability `2^−L`; cumulative compressed length = cumulative predictive log-loss) — *in-distribution only*.

**Compute discount (the real scalar).** Plain `L` is blind to forward-running cost. A theory-of-everything sits near the global optimum of `L` yet is predictively inert at macro scales: shortest description, astronomical computation between description and observable (Bennett **logical depth**). The descriptional optimum and the *usable* optimum diverge along the runtime axis alone. So:
```
quality ≈ best effective compression of the observables you care about,
          per unit forward-running cost, at your level of description
```
= description length **discounted by compute** (Levin `Kt`, Schmidhuber speed prior). Hence elegance is always the *effective* theory's (clean **and** cheap to run at your scale), and **interesting** is neither incompressible (noise) nor shallow (compresses to nothing) but **logically deep** — structure expensive to reach. Depth, not brevity, is what taste chases. The framing is metaphysically agnostic: it fails even in the maximally-materialist world where a TOE exists, so it assumes neither materialism nor a clean bottom.

## 2. The axes = endogenous supervision

The invariants are not orthogonal primitives. They are the **level and derivatives of the one scalar `L`**, differentiated against different variables — and each derivative is computed *against the agent's own model, not the world*, which is exactly why each is **label-free**. The list of axes and the list of training signals are the same list.

A scalar admits only two question-types — its value, or its slope along some direction — so the count is bounded by the number of meaningful directions to differentiate against. That number is small: the **tangent space of model-quality is low-dimensional**. Smallness is *inherited from that dimension, not asserted*. The trade is short **xor** strictly-orthogonal: shortness comes from the shared origin `L`, and the shared origin is what makes the axes non-independent.

| Axis / signal | differentiate `L` against | label-free because |
|---|---|---|
| **Compression** (level) | — | scored on own corpus |
| **Rigidity** / non-arbitrariness | perturbation of the object | you administer the perturbation |
| **Learning progress** | agent's own time on it | `−dL/d(engagement)`, vs own predictions |
| **Generativity** (≈ **empowerment**, channel capacity actions→futures) | forward moves | reachability inside own search |
| **Apparatus upgrade** / ontology revision | the **encoder itself** | retrospective recompression of own corpus |

*Resolved tension* is not separate — it's compression weighted by prior-violation. *Consilience* is generativity's static twin — agreement across independently-reached regions of the model.

**Axis 5 is the recursive term.** Axes 1–4 are scored by a fixed evaluator; axis 5 changes the evaluator, hence changes the function computing 1–4. Any flat decomposition drops it. It is the same object as "setting the goal" (§3) seen from inside: changing the evaluator vs. scoring within it.

**Why these are domain-general.** Every variable above — object, time, trajectory, encoder — is *not the domain*. So the axes are domain-free by construction: they are precisely the residual that survives scrubbing domain identity, the format-stripped quality signature. Stated as an objective: learn latent `z` maximizing `I(z; quality)` while minimizing `I(z; domain)` — what predicts quality once domain is unrecoverable. This sensor **self-assembles under multi-domain compression**: encoding "elegant" once and reusing it across domains is shorter than re-encoding per domain, so compression pressure factors it out — but only if the stream spans domains. The whole job of a curriculum is to make the cross-domain invariant the cheapest available encoding. (The estimator itself — the proof-nose, the ear — stays domain-bound; what transfers is this sensor plus the acquisition loop and the meta-calibration that runs it.)

**Where the signal lives.** The supervision is richest at the **boundary**. The interestingness gradient is the *convertible fraction of surprise* — `d/dt` of corpus compressibility — peaked in the middle, zero at noise (error, no assimilation) and at boredom (no error). Correspondingly, **comparison ≠ exposure**: exposure samples the distribution; comparison is **boundary-seeking sampling** at the decision surface, worth far more per example. Refined taste is robustness near that boundary — a verifier hardened against a generator tuned to fool a weak one.

## 3. The main goal is an input

Below a fixed top-level goal, every taste-act is ordinary value-estimation. "Positing an objective" decomposes into recognizing that the current position affords a high-generativity declaration, and timing it — both position-reads, teachable through the same signals. Given any goal above it, spawning sub-objectives collapses to generativity-estimation toward a fixed point: fully `V`-shaped, fully weightable.

The one act that is *not* estimation is setting the apex goal itself — the one with nothing above it. There "generativity toward" has no referent, and the read is self-fulfilling (pursuing it reorganizes the field around it): a fixed-point commitment, not a measurement. **So supply the apex as input.** Everything beneath it then runs on the five-axis value function (§2) over the compute-discounted scalar (§1). Authorship lives only at the top, and the top is given.