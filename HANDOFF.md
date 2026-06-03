# Handoff

Snapshot of where `hypertaste` stands and the three things to do next. For architecture,
the LLM-call map, the airgap model, and run instructions, see `README.md`; for what we
borrow from HyperAgents, see `REFERENCE.md`.

## Where we are
- Full DGM-H pipeline works: task agent (Haiku) ↔ meta agent (Opus) ↔ world-smith (Opus),
  archive evolution, objective WILT fitness + frozen transfer set. All via `claude -p`
  (subscription, no API key).
- **Efficiency done**: `episode_mode=single_session` runs a whole world's episode in one
  `claude -p` session via a stdio-MCP probe tool. Measured ~4.7× cheaper at 6 probes
  (1 call vs 7), trending to ~30× at the full 30-probe budget.
- **Loop closed**: ZPD difficulty escalation + world-smith targeting the agent's weak
  taste-modes; frozen transfer guards generalization.
- 6/6 tests pass. Mock loop improves 0.30→0.88 and escalates difficulty 2→3.
- Open gotcha recorded: `--permission-mode bypassPermissions` is refused as root; we use
  `acceptEdits` + an explicit `--allowedTools mcp__probe__*` allowlist.
- **TODO 1 done** (2026-06-03): first real 3-iteration evolution run completed. See below.

---

## TODO 1 — Short real multi-iteration run (single_session) — ✅ DONE (2026-06-03)
First end-to-end real evolution run completed. Full analysis + numbers:
[`runs/TODO1_FINDINGS.md`](runs/TODO1_FINDINGS.md); raw log: `runs/todo1_2026-06-03.log`.

**What happened:** pipeline ran 3 iterations with no crashes; archive grew to 4 valid
nodes (seed + 3 children); airgap held (no rule leaked into `EVAL_REPORT.md`); cost
**$2.47 / 30 calls** (as predicted). The Opus meta agent makes **substantial, sensible
edits** — all 3 children independently invent the same two mechanisms: a deterministic
*falsification-first probe battery* and a *verified Occam candidate-rule library* (so good
taste doesn't depend on the weak Haiku model). That answers the headline question — yes,
it edits `solver.py` non-trivially, far beyond the mock's strategy flip.

**But fitness did NOT climb** (child progression 0.609→0.465→0.553; transfer flat→down).
Three understood causes, each with a fix to carry into the next run:
1. **Meta agent exhausts its turn budget every iteration** (`turns=13, error=True` at
   `--meta-max-turns 12`) → edits get cut off mid-revision. **Bump `meta_max_turns` to
   ~25–40.**
2. **No cumulative lineage** — `select_parent` (random, RNG seeded by iter index) picked
   the seed `gen_0000` all 3 times, so every child is "seed + one edit" and nothing
   compounds. **Bias selection toward best/recent children** (the deferred `score×novelty`
   selector in REFERENCE.md), or fix the RNG seeding so lineage advances.
3. **Noisy 4-world fitness + stochastic Haiku** — the same seed program scored
   0.76/0.43/0.58 across iters (driven by the regenerated curriculum, not the agent), so a
   better child can still lose. **More worlds/repeats per eval** (+ staged-eval gating to
   stay cheap).

**Loop mechanics that worked:** weak-tag targeting closed (iters 2–3 hit `gen_0001`'s
`sign_zero`/`arithmetic` weaknesses, making train worlds materially harder); single-session
economics held (24 Haiku episodes ≈ $1); invalid-child handling never tripped. ZPD
difficulty stayed at 2 (escalation needs ≥75% solved; best agent hit 2/4) — gated behind
fixes 1–2 above.

**Reproduce:**
```bash
python run_loop.py --iterations 3 --backend real --episode-mode single_session \
  --max-probes 8 --n-train 2 --n-transfer 2 --meta-max-turns 12
```

---

## TODO 2 — Brainstorm: how we grow the world — ✅ DONE (2026-06-03)
Design note written: [`WORLD_DESIGN.md`](WORLD_DESIGN.md).

**Pick:** grow along two coupled axes first, chosen because both keep the empirical-
equivalence scorer and the AST airgap byte-for-byte unchanged:
- **Axis A — compositional / multi-rule worlds** (regimes, exceptions, conjunctions).
  The grammar *already* admits `and/or/not`, ternaries, and arithmetic, so these are
  expressible and safe today; they're exactly where taste (hypothesis decomposition,
  falsification) wins. Scorer change: **none** (still pure `f(x,y,z)→bool`).
- **Axis B — generative/sampled hypothesis space** (required enabler for A). The
  info-gain metric currently measures reduction over the fixed 25-rule
  `candidate_library`; compositional rules fall outside it, so `avg_info_gain` goes
  noisy. Fix: measure version-space collapse over rules *sampled from the grammar*;
  demote the library to prior/fallback + offline Occam inductor.

**Deferred (with reasons in the note):** stochastic rules and latent/multi-step rules
(both break deterministic empirical-equivalence scoring — need new scorers/metrics),
N>3 vars (orthogonal), and program/dataset "real research" worlds (long-term).

**Resolved open questions** (anti-degeneracy via a non-degenerate+solvable gate,
objective world-novelty via battery behavior-vector de-dup, anti-collusion via an
independently-seeded transfer distribution, and keeping LLM "interestingness" in world
*generation* only — never in fitness). See `WORLD_DESIGN.md` for the smallest
shippable first slice + the exact files each change touches.

Original brainstorm framing (for reference):

**Goal:** decide how the world evolves beyond classic numeric WILT so that *research taste*
keeps being the thing that wins, without breaking objective scoring or the airgap.

**Axes to grow (candidates):**
- **Wider rules:** N>3 variables; vectors/sequences instead of triples.
- **Latent state / multi-step:** rules with hidden internal state, or that depend on the
  *history* of probes (sequential structure), pushing beyond single-shot boolean rules.
- **Compositional / multi-rule worlds:** conjunctions/disjunctions, exceptions, regimes
  ("rule A below 0, rule B above") — rewards hypothesis decomposition.
- **Noise / stochastic rules:** probabilistic labels — forces repeated probing and
  statistical reasoning (changes the "no value in repeating a probe" assumption; revisit
  the novelty metric).
- **Richer grammars / procedural generation:** an Opus-grown grammar (the current candidate
  library is fixed and doubles as the hypothesis space — decouple these as worlds get rich).
- **Toward "real research" worlds:** eventually a world whose rule is a small program,
  dataset regularity, or simulated system — the long-term "solve the world" target.

**Open questions to resolve in the brainstorm:**
- How to keep **objective scoring** as worlds get richer (empirical equivalence still works
  for deterministic rules; what's the scorer for stochastic/multi-step worlds?).
- How does the **hypothesis-space-reduction / info-gain** metric scale when the candidate
  library no longer covers the rule space? (Need a generative or sampled hypothesis space.)
- **ZPD calibration + diversity:** how does the world-smith avoid both unsolvable worlds and
  degenerate/colluding ones? How do we measure world *novelty* across generations?
- What's the **anti-collusion guarantee** as the smith gets more powerful — is a frozen
  held-out set enough, or do we need an independently-generated transfer distribution?
- Where does **LLM-judged "interestingness"** belong (world generation only) vs. objective
  signals (agent fitness)?

**Output:** a short design note (could live in `REFERENCE.md` or a new `WORLD_DESIGN.md`)
picking the first 1–2 axes to implement and the scorer/metric changes they require.

---

## TODO 3 — Containerization (production-grade airgap)
**Goal:** isolate the self-modifying meta agent (and ideally the whole agent plane) in a
container so a runaway/self-modifying agent cannot touch the host, secrets, or the world
source. Today the meta agent is airgapped only by *denying Bash*; that's the lighter
mitigation, not a hard boundary.

**Approach (mirror HyperAgents — see `REFERENCE.md`):**
- Dockerfile for the agent plane; run the meta agent **in-container** with only the child
  workspace mounted (no host FS, no `.env`, no world source).
- Edit → extract diff → reset container between generations.
- No network (or a strict egress policy) inside the agent container; `claude -p` runs from
  the host/orchestrator, the *edits* happen in the container.
- Keep the world (`hta/world/*`, the probe server) outside the agent container; the only
  channel remains the probe MCP tool.

**Open questions:** how `claude -p` agentic editing composes with a container boundary
(run claude inside, or mount the workspace and run claude on the host?); how to sandbox the
single-session task episode's MCP server vs. the agent session; resource limits.

**Done when:** the meta agent runs with no readable path to host secrets or the world, the
edit→diff→reset cycle works, and the existing tests still pass against the containerized path.
