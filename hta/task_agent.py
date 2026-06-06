"""Task agent: load an (editable) solver program and run it against worlds.

The solver is the unit that evolves. It is loaded from a directory's `solver.py`
and given (a) a ProbeChannel and (b) a constrained-generation llm callable bound to
the TASK model (Haiku). The solver never imports from hta.world -- it only sees
boolean probe results.
"""

import importlib.util
import hashlib
import json
import os
import sys
import tempfile
import uuid
from collections import defaultdict
from typing import Callable, List

from . import llm
from .config import Config
from . import taste
from .world.engine import WiltWorld

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    """Dispatch on execution mode. single_session (real) runs a whole episode in one
    claude -p session via the probe MCP tool; per_probe (and mock) makes one call per
    probe. Both return the same {history, guess, metrics} shape."""
    if cfg.episode_mode == "single_session" and cfg.backend != "mock":
        return _run_single_session(solver, world, cfg, log)
    return _run_per_probe(solver, world, cfg, log)


def _score_and_metrics(world: WiltWorld, history, guess, cfg: Config) -> dict:
    score = world.score_guess(guess)
    hyp = world.hypothesis_reduction(history)
    metrics = taste.compute_metrics(history, guess, score, hyp)
    metrics["fitness"] = taste.fitness(metrics, cfg)
    return {"history": history, "guess": guess, "metrics": metrics}


def _run_per_probe(solver, world: WiltWorld, cfg: Config, log=print) -> dict:
    channel = world.open_channel()
    llm_fn = _task_llm(cfg)
    guess = None
    try:
        guess = solver.run(channel, llm_fn)
    except Exception as e:
        log(f"  solver crashed on a world: {e}")
        guess = None
    return _score_and_metrics(world, channel.history(), guess, cfg)


def _run_single_session(solver, world: WiltWorld, cfg: Config, log=print) -> dict:
    traj_path = os.path.join(tempfile.gettempdir(), f"hta_traj_{uuid.uuid4().hex}.jsonl")
    open(traj_path, "w").close()
    # The rule source lives ONLY in the MCP server's env; the agent session cannot read it.
    server_env = {
        "HTA_RULE_SRC": world.rule.source,
        "HTA_MAX_PROBES": str(world.max_probes),
        "HTA_TRAJ_PATH": traj_path,
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONPATH": _REPO_ROOT + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    server_argv = [sys.executable, "-m", "hta.world.probe_server"]
    try:
        prompt = solver.episode_prompt(world.max_probes)
    except Exception as e:
        log(f"  solver has no episode_prompt ({e}); using default")
        prompt = _default_episode_prompt(world.max_probes)
    max_turns = world.max_probes * 2 + cfg.episode_turn_buffer
    res = llm.episode(prompt, model=cfg.task_model, mcp_server_argv=server_argv,
                      server_env=server_env, cwd=_REPO_ROOT,
                      allowed_tools=cfg.episode_allowed_tools, max_turns=max_turns,
                      role="task_episode", cfg=cfg)
    if res.get("is_error"):
        log(f"  episode error: {str(res.get('result'))[:140]}")
    history, guess = _read_trajectory(traj_path)
    try:
        os.remove(traj_path)
    except OSError:
        pass
    return _score_and_metrics(world, history, guess, cfg)


def _read_trajectory(path: str):
    """Reconstruct (history, guess) from the server's append-only log. history items
    match channel.history() shape, so downstream scoring/metrics are unchanged."""
    history, guess = [], None
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("type") == "probe":
                    history.append({k: rec[k] for k in ("triple", "label", "reused", "malformed")
                                    if k in rec})
                elif rec.get("type") == "guess":
                    guess = rec.get("rule") or None
    except OSError:
        pass
    return history, guess


def _default_episode_prompt(max_probes: int) -> str:
    # Neutral fallback (no strategy steering): state the task and the protocol only.
    return (
        "Discover a hidden rule mapping three numbers (x,y,z) to True/False. "
        f"You have {max_probes} probes. Use probe(x,y,z) to gather evidence, then call "
        "submit_guess('lambda x, y, z: ...') exactly once with a rule consistent with "
        "all observations."
    )


def _aggregate_repeats(recs: List[dict]) -> dict:
    """Collapse N repeated episodes of ONE world into a single record: average the
    numeric taste metrics (shrinking Haiku's run-to-run noise) and majority-vote the
    boolean `solved`. The first repeat's trajectory/guess is kept for the qualitative
    parts of the report, so the per_world shape is unchanged downstream."""
    base = dict(recs[0])
    metrics_list = [r["metrics"] for r in recs]
    agg = dict(metrics_list[0])
    numeric = ("fitness", "agreement", "novelty", "reuse_rate", "avg_info_gain",
               "hyp_reduced_frac", "occam", "false_frac", "probes_used", "malformed")
    for k in numeric:
        vals = [m[k] for m in metrics_list if k in m]
        if vals:
            agg[k] = round(sum(vals) / len(vals), 4)
    solved_votes = sum(1 for m in metrics_list if m.get("solved"))
    agg["solved"] = solved_votes * 2 >= len(metrics_list)  # majority of repeats recovered it
    base["metrics"] = agg
    return base


def evaluate(solver_dir: str, worlds: List[WiltWorld], cfg: Config, log=print) -> dict:
    """Evaluate a solver across worlds. Returns aggregate numbers plus a SANITIZED
    report (no rule names/sources) suitable to hand to the meta agent. With
    cfg.eval_repeats > 1, each world's episode is run that many times and averaged to
    damp the weak task model's variance (see Config.eval_repeats).

    Real-backend episodes are independent claude -p subprocesses, so the (world x
    repeat) units run concurrently (cfg.eval_concurrency) -- this is the dominant
    wall-clock lever, since serial episodes were ~half the run time. The mock backend
    stays serial so its tests remain deterministic. Results are regrouped per world and
    logged in order, so output is unchanged from the serial version."""
    solver = load_solver(solver_dir)
    repeats = max(getattr(cfg, "eval_repeats", 1) or 1, 1)
    concurrency = max(getattr(cfg, "eval_concurrency", 1) or 1, 1)
    units = [i for i in range(len(worlds)) for _ in range(repeats)]  # world idx per episode
    recs_by_world: dict = {i: [] for i in range(len(worlds))}

    if cfg.backend == "mock" or concurrency <= 1 or len(units) <= 1:
        for i in units:
            recs_by_world[i].append(run_on_world(solver, worlds[i], cfg, log=log))
    else:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(concurrency, len(units))) as ex:
            for i, rec in ex.map(lambda i: (i, run_on_world(solver, worlds[i], cfg, log=log)),
                                 units):
                recs_by_world[i].append(rec)

    per_world = []
    for i, w in enumerate(worlds):
        recs = recs_by_world[i]
        rec = recs[0] if len(recs) == 1 else _aggregate_repeats(recs)
        per_world.append(rec)
        m = rec["metrics"]
        rpt = "" if repeats == 1 else f" (avg of {repeats})"
        log(f"  world_{i}: solved={m['solved']} agree={m['agreement']:.2f} "
            f"probes={m['probes_used']} novelty={m['novelty']:.2f} "
            f"infogain={m['avg_info_gain']:.2f}{rpt}")
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


def weak_tags(worlds: List[WiltWorld], per_world: List[dict], threshold: float = 0.5) -> List[str]:
    """Taste-tags the agent is weakest at: rule tags with the lowest solved-rate.
    Feeds the world-smith so the curriculum targets the agent's blind spots."""
    total, solved = defaultdict(int), defaultdict(int)
    for w, r in zip(worlds, per_world):
        for tag in w.rule.tags:
            total[tag] += 1
            if r["metrics"]["solved"]:
                solved[tag] += 1
    rates = {t: solved[t] / total[t] for t in total}
    weak = [t for t, rt in rates.items() if rt < threshold]
    return sorted(weak, key=lambda t: rates[t])


def weakness_flags(per_world: List[dict]) -> List[str]:
    """Dominant structural failure modes, measured against MODEL-FREE reference points
    rather than an absolute bar tuned to one task model -- so the diagnosis stays valid
    when the task model changes. The information ideal is 0.5: a binary-splitting probe
    halves the version space (avg_info_gain -> 0.5) and balanced, falsification-seeking
    probing returns False about half the time (false_frac -> 0.5). An axis is flagged
    when the agent sits below half of that ideal."""
    n = len(per_world) or 1
    mig = sum(r["metrics"]["avg_info_gain"] for r in per_world) / n
    mff = sum(r["metrics"]["false_frac"] for r in per_world) / n
    overcomplex = sum(1 for r in per_world
                      if r["metrics"]["agreement"] >= 0.95 and not r["metrics"]["solved"])
    ideal = 0.5  # halving / balanced-probing point; information-theoretic, not model-tuned
    flags = []
    if mig < ideal / 2:
        flags.append("weak hypothesis-space reduction (low info gain)")
    if mff < ideal / 2:
        flags.append("confirmation bias (rarely seeks falsifying cases)")
    if overcomplex > 0:
        flags.append("over-complex guesses (near-correct but not exact)")
    return flags


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
