# Reference: how HyperAgents does it (and what we borrow)

We did **not** fork [facebookresearch/Hyperagents](https://github.com/facebookresearch/Hyperagents)
(CC-BY-NC-SA; heavy litellm/Docker/multi-domain runtime whose LLM layer we'd have to rip out
for `claude -p`). Instead we kept our lean reimplementation and use their repo as a *reference*.
This file is notes + pointers (no code copied — copying their NC-licensed code would infect our
repo's license). Line numbers are from the repo state we read on 2026-06-03.

## How they do the pieces

1. **Generation loop** — `generate_loop.py:719-1022` drives generations; `generate()`
   (`generate_loop.py:427`) does: create Docker container → apply parent-lineage diffs → run the
   meta agent → **staged eval** on a small subset with early-stop gating (`generate_loop.py:638-684`)
   → full eval → archive *after* eval (`gl_utils.py:160-176`) → select next parent
   (`generate_loop.py:1006-1017`).

2. **Self-improvement instruction (DGM)** — not fixed; **LLM-generated per iteration from a
   sampled failure**. `baselines/dgm/utils.py:230-260` (`get_problem_statement`) samples a failed
   example, calls the model with a `DIAGNOSE_PROMPT` (`:63-100`) over the agent code + eval report
   + chat log, and formats the result into a problem description.

3. **Docker sandbox** — the self-modifying agent runs entirely in a container; it edits code
   *in-container*, the diff is extracted afterward, and the container is reset (`git reset --hard`,
   `git clean -fd`). `docker_utils.py:102-150` (build/start), `gl_utils.py:438-508` (apply diffs
   in container), `generate_loop.py:427-480, 693-700`.

4. **Archive & parent selection** — archive is JSONL (`gl_utils.py:160-176`). Default selection is
   `score_child_prop` (`gl_utils.py:511-587`): sigmoid score-weight × an inverse-child-count
   novelty penalty `exp(-(count/8)^3)` — balances quality and freshness. Random selection lives in
   the standalone `select_next_parent.py` (kept editable).

5. **Multi-turn efficiency** — within one generation they accumulate `msg_history` across tool
   calls (`agent/llm_withtools.py:91-174`); fresh history per generation
   (`meta_agent.py:18`). They use raw litellm, so there's no big per-call system-prompt tax — which
   is exactly the `claude -p`-specific cost we solve with single-session episodes.

## Our module ↔ theirs

| ours | theirs |
|---|---|
| `hta/loop.py` | `generate_loop.py` (`generate()` + loop) |
| `hta/archive.py` | `gl_utils.py` archive + `select_next_parent.py` |
| `hta/meta_agent.py` | `meta_agent.py` + DGM `get_problem_statement` |
| `hta/llm.py` (`complete`/`agentic`/`episode`) | `agent/llm.py` + `agent/llm_withtools.py` |
| `hta/world/*` (WILT) | their `domains/*` (per-domain harnesses) |

## Patterns to adopt next (deferred this session)

- ~~**Docker-per-generation sandbox for the meta agent**~~ — **DONE (TODO 3)**. Mirrors
  `docker_utils.py` + in-container edit→diff→reset as `hta/sandbox.py:DockerSandbox`
  (`--sandbox docker`): claude runs inside an ephemeral, host-isolated container; copy
  workspace in → edit → copy out → apply diff → `rm`.
- **Staged-eval gating** — eval each child on a tiny world subset first; only run the full set if
  it clears a threshold. Cuts compute (`generate_loop.py:638-684`).
- **score×novelty parent selection** — replace our `random.choice` in `hta/archive.py:select_parent`
  with `score_child_prop`-style weighting (`gl_utils.py:557-584`).
- **Diagnose-from-sampled-failure** — feed the meta agent a *specific* sampled failing trajectory
  (we already pass a sanitized whole-eval report; sampling one failure is cheaper and sharper).
