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

from . import sandbox
from .config import Config

_INSTRUCTION = """You are the META AGENT in a self-improving research system.

GOAL: improve the TASK AGENT so it investigates an unknown world better -- so it grows
better *research taste*. You are NOT given a checklist of what good taste is, and you
must NOT assume one: read the agent's actual behavior and let the evidence tell you
where its inquiry was weak. (A fix copied from a fixed list is the designer's taste
re-installed, not the agent's taste grown -- that is exactly what this system exists to
get past. Diagnose from what happened, not from a template.)

You are in the task agent's own workspace. Files:
  - `solver.py`         : the editable task-agent program (it defines class Solver).
  - `meta_strategy.md`  : YOUR editable playbook for how to improve the task agent.
  - `EVAL_REPORT.md`    : how the current solver behaved -- its own probe trajectory,
                          the results it observed, its final answers, and outcome
                          metrics. The hidden answers themselves are NOT given and you
                          must not try to reconstruct them; reason only about the
                          agent's *conduct*, never the world's secrets.

YOUR PLAYBOOK (meta_strategy.md) says:
---
{meta_strategy}
---

DO THIS:
1. Read EVAL_REPORT.md and solver.py.
2. From the trajectory and outcomes alone, infer the single most impactful weakness in
   how this agent investigates -- where did its choices waste the budget or fail to
   reduce its uncertainty? Name the weakness you actually see; do not pattern-match.
3. Edit solver.py to fix that weakness with the smallest general change that would help
   ANY agent with it (prefer structure -- how it allocates probes, tracks what it knows,
   decides when to stop -- over surface wording). Keep it a valid Python file that still
   defines class Solver with run(self, channel, llm); do not import any world/engine
   internals; interact only via the channel and the llm callable. Keep the program
   short -- a shorter program that explains more behavior has captured a more general
   regularity (favor fitness-per-bit, not size for its own sake).
4. If you found a better general improvement *procedure*, also improve meta_strategy.md.

Make concrete edits now. Do not ask questions."""


def _read(path, default=""):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return default


def self_modify(parent_dir: str, child_dir: str, report_md: str, cfg: Config, log=print,
                instruction_template: str = None) -> str:
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
    # The instruction is world-agnostic by default (Chapter 1's contract); a chapter with a
    # different task-agent contract (e.g. Chapter 2's harness, run(self, ctx) -> list[int])
    # passes its own template. Both are filled with the editable meta_strategy.md.
    instruction = (instruction_template or _INSTRUCTION).format(meta_strategy=meta_strategy)
    # Route the agentic edit through the configured sandbox: DirectSandbox (Bash-denied,
    # in-process) by default, or DockerSandbox (hard, host-isolated container) when
    # cfg.sandbox == "docker". Both return the same result shape.
    res = sandbox.get_sandbox(cfg).run_meta_edit(child_dir, instruction, cfg, log=log)
    log(f"  meta agent [{cfg.sandbox}]: turns={res.get('num_turns')} "
        f"error={res.get('is_error')} cost=${res.get('cost_usd', 0):.3f}")
    return child_dir


def _mock_self_modify(child_dir: str, log=print):
    """Deterministic mock edit: flip the seed program's mock-fixture variant
    seed->edited so the offline plumbing shows a behavior change. This is a PLUMBING
    STUB, not a model of taste discovery -- it carries no diagnosis and encodes no
    answer; the real meta agent (Opus) does the actual diagnose-from-evidence work."""
    solver_path = os.path.join(child_dir, "solver.py")
    src = _read(solver_path)
    new = re.sub(r'_MOCK_VARIANT\s*=\s*"seed"', '_MOCK_VARIANT = "edited"', src, count=1)
    if new != src:
        with open(solver_path, "w") as f:
            f.write(new)
        log("  meta agent (mock): flipped _MOCK_VARIANT seed -> edited (plumbing stub)")
    else:
        log("  meta agent (mock): no seed variant found; left solver unchanged")
    ms_path = os.path.join(child_dir, "meta_strategy.md")
    ms = _read(ms_path)
    ms += "\n\n## Improvement log\n- (mock) flipped the seed program's fixture variant.\n"
    with open(ms_path, "w") as f:
        f.write(ms)
