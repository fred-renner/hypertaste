# Handoff

Snapshot of where `hypertaste` stands. The three TODOs below are **all done** (TODO 1:
first real run; TODO 2: world-growth design; TODO 3: containerized airgap). For
architecture, the LLM-call map, the airgap model, and run instructions, see `README.md`;
for what we borrow from HyperAgents, see `REFERENCE.md`; for the container airgap, see
`hta/sandbox.py`.

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
- **TODO 2 done** (2026-06-03): world-growth design note (`WORLD_DESIGN.md`). See below.
- **TODO 3 done** (2026-06-03): production-grade container airgap for the meta agent
  (`--sandbox docker`, `hta/sandbox.py`, `docker/Dockerfile.agent`). See below.

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
Three understood causes, each with a fix — **all three now implemented (2026-06-04)**:
1. **Meta agent exhausts its turn budget every iteration** (`turns=13, error=True` at
   `--meta-max-turns 12`) → edits get cut off mid-revision. ✅ **`meta_max_turns` default
   raised 30→40** (`hta/config.py`) so a multi-file edit finishes cleanly.
2. **No cumulative lineage** — `select_parent` (random) picked the seed `gen_0000` all 3
   times, so every child was "seed + one edit" and nothing compounded. ✅ **Default parent
   selection is now `weighted`** (`hta/archive.py`): quality (sigmoid of fitness) × novelty
   (inverse child-count), the `score_child_prop` shape from REFERENCE.md. A thrice-branched
   seed drops to ~1% selection while the fittest fresh child dominates, so lineage advances.
   `--parent-selection random` restores the old policy.
3. **Noisy 4-world fitness + stochastic Haiku** — the same seed program scored
   0.76/0.43/0.58 across iters, so a better child can still lose. ✅ **`eval_repeats` knob
   added** (`hta/config.py`, `--eval-repeats N`): re-runs each world's episode N times and
   averages the taste metrics (majority-vote on `solved`), damping the variance. Default 1
   (mock pipeline unchanged); real runs raise it (cost scales ×N — pair with staged-eval
   gating, still deferred in REFERENCE.md, to stay cheap).

**Loop mechanics that worked:** weak-tag targeting closed (iters 2–3 hit `gen_0001`'s
`sign_zero`/`arithmetic` weaknesses, making train worlds materially harder); single-session
economics held (24 Haiku episodes ≈ $1); invalid-child handling never tripped. ZPD
difficulty stayed at 2 (escalation needs ≥75% solved; best agent hit 2/4) — gated behind
fixes 1–2 above.

**Reproduce the original run** (pre-fix knobs, for the record):
```bash
python run_loop.py --iterations 3 --backend real --episode-mode single_session \
  --max-probes 8 --n-train 2 --n-transfer 2 --meta-max-turns 12
```
**Next run with the fixes** (weighted lineage + repeats + roomy meta budget):
```bash
python run_loop.py --iterations 3 --backend real --episode-mode single_session \
  --max-probes 8 --n-train 3 --n-transfer 2 --eval-repeats 2
# meta_max_turns now defaults to 40; parent_selection defaults to weighted
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

## TODO 3 — Containerization (production-grade airgap) — ✅ DONE (2026-06-03)
A `Sandbox` strategy (`hta/sandbox.py`) selected by `--sandbox`:
- `none` → `DirectSandbox` (default, unchanged: `claude -p` in-process, Bash denied);
- `docker` → `DockerSandbox` — the hard boundary. Per child: `docker create` (no host
  bind mounts, `--network/--memory/--cpus/--pids-limit`, `--cap-drop ALL`,
  `no-new-privileges`) → `cp` workspace in → `start` (claude edits **in-container**) →
  `cp` result out → apply diff → `rm`. Image `docker/Dockerfile.agent` (Node + claude
  CLI, non-root, no project code/world/secrets), built by `scripts/build_agent_image.sh`.

Design decisions: claude runs **inside** the container (the only way to actually contain
Edit/Read/Write); credentials forwarded as **env**, never mounted files (a no-Bash agent
can't read its own env); `--sandbox docker` **fails closed** if Docker is unavailable.
Deferred: containerizing the task-episode MCP server (the probe server owns the rule and
must stay outside the agent container — different shape, lower risk).

**Done when — status:** ✅ no readable path to host secrets/world; ✅ edit→diff→reset
works; ✅ tests pass (6 pipeline + 10 sandbox = 16). The full create→cp→start→cp→diff→rm
cycle + all isolation flags were validated against a **live daemon** (the only piece not
run live is the literal claude call: blocked here by a Docker Hub pull rate-limit on the
node base and this managed env's host-proxy auth — both environmental, not code).

**Run:** `scripts/build_agent_image.sh` once, then
`python run_iteration.py --backend real --sandbox docker --episode-mode single_session`.
