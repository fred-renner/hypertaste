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

---

## TODO 1 — Short real multi-iteration run (single_session)
**Goal:** see the *real* Opus meta agent invent novel taste improvements across generations
(the mock plateaus because it only has one trick: flip naive→smart). This is the first
end-to-end real evolution run, now affordable thanks to single-session episodes.

**Run:**
```bash
python run_loop.py --iterations 3 --backend real --episode-mode single_session \
  --max-probes 8 --n-train 2 --n-transfer 2 --meta-max-turns 12
```
Rough budget: ~4 episodes × 2 (parent+child) + 1 Opus meta + 1 Opus world-smith per
iteration ≈ $0.5–1.0 and a few minutes per iteration; ~$2–3 total for 3 iterations.

**What to watch:** fitness progression per generation; whether the Opus meta agent edits
`solver.py`/`episode_prompt.md` in non-trivial ways (beyond the strategy flip); whether
`weak_tags` get targeted by the next curriculum; transfer-set fitness (the real signal —
did taste *generalize*, not just fit the training worlds).

**Watch out for:** `--max-turns` budget vs `max_probes` (episode buffer is 8; bump if the
agent runs out of turns mid-episode); a child that breaks the `Solver` contract should be
recorded `valid=False` (already handled) — confirm it doesn't crash the loop.

**Done when:** a real run completes 3 iterations, the archive grows with valid children,
and we can read off whether transfer fitness rose. Capture the run log for analysis.

---

## TODO 2 — Brainstorm: how we grow the world
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
