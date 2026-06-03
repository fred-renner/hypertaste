"""Meta agent: branch a parent hyperagent and self-modify it to improve research
taste. This is the DGM-H self-modification step, run as an AGENTIC `claude -p`
(Opus) inside the child's workspace.

Airgap: the child workspace contains only the editable program (solver.py,
meta_strategy.md) plus the SANITIZED eval report. The meta agent is granted
Edit/Read/Write (no Bash) and never executes the solver against a world -- so it
can shape *behavior* but can never observe a hidden rule.

Metacognitive self-modification: meta_strategy.md is itself part of the editable
program. The meta agent is told it may improve that file too, so the procedure that
generates future improvements can itself evolve.
"""

import os
import re
import shutil

from . import llm
from .config import Config

_INSTRUCTION = """You are the META AGENT in a self-improving research system.

GOAL: improve the TASK AGENT so it develops better *research taste* on an inductive
"discover the hidden rule" task (Wason 2-4-6 style). Good research taste means:
  - propose probes that FALSIFY hypotheses and split the space (not confirm bias),
  - never waste turns repeating probes or emitting malformed ones,
  - reduce the hypothesis space efficiently across turns,
  - finally guess the SIMPLEST rule consistent with the evidence (Occam).

You are in the task agent's own workspace. Files:
  - `solver.py`         : the editable task-agent program (it defines class Solver).
  - `meta_strategy.md`  : YOUR editable playbook for how to improve the task agent.
  - `EVAL_REPORT.md`    : how the current solver behaved (its probes, the booleans it
                          observed, its guesses, and taste metrics). The hidden rules
                          themselves are NOT given and you must not try to guess them.

YOUR PLAYBOOK (meta_strategy.md) says:
---
{meta_strategy}
---

DO THIS:
1. Read EVAL_REPORT.md and solver.py.
2. Diagnose where research taste failed (confirmation bias, repeats, over-complex
   guesses, poor space reduction).
3. Edit solver.py to fix the most impactful weakness. Keep it a valid Python file
   that still defines class Solver with run(self, channel, llm). Do not import any
   world/engine internals; interact only via the channel and the llm callable.
4. If you found a better general improvement procedure, also improve meta_strategy.md.

Make concrete edits now. Do not ask questions."""


def _read(path, default=""):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return default


def self_modify(parent_dir: str, child_dir: str, report_md: str, cfg: Config, log=print) -> str:
    if os.path.exists(child_dir):
        shutil.rmtree(child_dir)
    shutil.copytree(parent_dir, child_dir)
    # strip caches that may have been copied
    for junk in ("__pycache__",):
        p = os.path.join(child_dir, junk)
        if os.path.isdir(p):
            shutil.rmtree(p)
    with open(os.path.join(child_dir, "EVAL_REPORT.md"), "w") as f:
        f.write(report_md)

    if cfg.backend == "mock":
        _mock_self_modify(child_dir, log)
        return child_dir

    meta_strategy = _read(os.path.join(child_dir, "meta_strategy.md"), "(empty)")
    instruction = _INSTRUCTION.format(meta_strategy=meta_strategy)
    res = llm.agentic(instruction, workdir=child_dir, model=cfg.meta_model,
                      allowed_tools=cfg.meta_allowed_tools, max_turns=cfg.meta_max_turns,
                      role="meta", cfg=cfg)
    log(f"  meta agent: turns={res.get('num_turns')} error={res.get('is_error')} "
        f"cost=${res.get('cost_usd', 0):.3f}")
    return child_dir


def _mock_self_modify(child_dir: str, log=print):
    """Deterministic improvement: flip the solver's strategy knob naive->smart and
    record the change in the playbook. Mirrors what a real meta agent would do, but
    reproducibly and for free."""
    solver_path = os.path.join(child_dir, "solver.py")
    src = _read(solver_path)
    new = re.sub(r'STRATEGY\s*=\s*"naive"', 'STRATEGY = "smart"', src, count=1)
    if new != src:
        with open(solver_path, "w") as f:
            f.write(new)
        log("  meta agent (mock): switched STRATEGY naive -> smart")
    else:
        log("  meta agent (mock): no naive strategy found; left solver unchanged")
    ms_path = os.path.join(child_dir, "meta_strategy.md")
    ms = _read(ms_path)
    ms += ("\n\n## Improvement log\n- Switched probing strategy to 'smart' "
           "(falsification + Occam induction) after observing confirmation-bias "
           "failures in EVAL_REPORT.md.\n")
    with open(ms_path, "w") as f:
        f.write(ms)
