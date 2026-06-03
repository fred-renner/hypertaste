"""Task agent: load an (editable) solver program and run it against worlds.

The solver is the unit that evolves. It is loaded from a directory's `solver.py`
and given (a) a ProbeChannel and (b) a constrained-generation llm callable bound to
the TASK model (Haiku). The solver never imports from hta.world -- it only sees
boolean probe results.
"""

import importlib.util
import hashlib
import os
from typing import Callable, List

from . import llm
from .config import Config
from . import taste
from .world.engine import WiltWorld


def load_solver(solver_dir: str):
    path = os.path.join(solver_dir, "solver.py")
    mod_name = "hta_solver_" + hashlib.md5(os.path.abspath(path).encode()).hexdigest()[:10]
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "Solver"):
        raise AttributeError(f"{path} does not define a Solver class")
    return module.Solver()


def _task_llm(cfg: Config) -> Callable:
    def call(prompt: str, role: str = "probe") -> str:
        return llm.complete(prompt, model=cfg.task_model, role=role, cfg=cfg)
    return call


def run_on_world(solver, world: WiltWorld, cfg: Config, log=print) -> dict:
    channel = world.open_channel()
    llm_fn = _task_llm(cfg)
    guess = None
    try:
        guess = solver.run(channel, llm_fn)
    except Exception as e:
        log(f"  solver crashed on a world: {e}")
        guess = None
    history = channel.history()
    score = world.score_guess(guess)
    hyp = world.hypothesis_reduction(history)
    metrics = taste.compute_metrics(history, guess, score, hyp)
    metrics["fitness"] = taste.fitness(metrics, cfg)
    return {"history": history, "guess": guess, "metrics": metrics}


def evaluate(solver_dir: str, worlds: List[WiltWorld], cfg: Config, log=print) -> dict:
    """Evaluate a solver across worlds. Returns aggregate numbers plus a SANITIZED
    report (no rule names/sources) suitable to hand to the meta agent."""
    solver = load_solver(solver_dir)
    per_world = []
    for i, w in enumerate(worlds):
        rec = run_on_world(solver, w, cfg, log=log)
        per_world.append(rec)
        m = rec["metrics"]
        log(f"  world_{i}: solved={m['solved']} agree={m['agreement']:.2f} "
            f"probes={m['probes_used']} novelty={m['novelty']:.2f} infogain={m['avg_info_gain']:.2f}")
    fitnesses = [r["metrics"]["fitness"] for r in per_world]
    solved = sum(1 for r in per_world if r["metrics"]["solved"])
    agg = {
        "mean_fitness": round(sum(fitnesses) / len(fitnesses), 4) if fitnesses else 0.0,
        "solved": solved,
        "n_worlds": len(worlds),
        "per_world": per_world,
        "report_md": _sanitized_report(per_world),
    }
    return agg


def _sanitized_report(per_world: List[dict]) -> str:
    """Markdown digest for the meta agent. Includes the agent's OWN observations
    (probe trajectories + booleans + guesses + taste metrics) but NEVER the hidden
    rule's name or source -- so the meta agent cannot learn answers, only behavior."""
    lines = ["# Evaluation report (sanitized)\n",
             "Each world's hidden rule is unknown to you. Below are the solver's own",
             "probes, the True/False it observed, its final guess, and taste metrics.\n"]
    for i, r in enumerate(per_world):
        m = r["metrics"]
        lines.append(f"\n## world_{i}")
        lines.append(f"- solved (exact rule recovery): **{m['solved']}**, "
                     f"agreement={m['agreement']:.2f}")
        lines.append(f"- probes_used={m['probes_used']}, novelty={m['novelty']:.2f}, "
                     f"reuse_rate={m['reuse_rate']:.2f}, malformed={m['malformed']}")
        lines.append(f"- avg_info_gain={m['avg_info_gain']:.2f} "
                     f"(hypothesis-space reduced {m['hyp_reduced_frac']*100:.0f}%), "
                     f"occam={m['occam']:.2f}, false_frac={m['false_frac']:.2f}")
        lines.append(f"- final guess: `{m['guess']}`")
        traj = []
        for h in r["history"]:
            if h.get("malformed"):
                traj.append("(malformed)->False")
            else:
                traj.append(f"{tuple(h['triple'])}->{h['label']}"
                            + ("[REPEAT]" if h.get("reused") else ""))
        lines.append(f"- trajectory: {'; '.join(traj)}")
    return "\n".join(lines)
