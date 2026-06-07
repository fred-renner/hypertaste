"""The Chapter-2 meta-agent-on-program loop, one iteration at a time.

This is the loop CLAUDE.md -> "Next action" names: search **scaffold-space** for the program
that makes a fixed weak student (Haiku) tasteful on the calibrated register world `trap-tetra`.
It reuses the Chapter-1 DGM-H machinery wholesale — the archive (`hta.archive`), the open-ended
parent selection, the Opus self-modify step (`hta.meta_agent`), the safe solver loader, the MDL
prior on program size — and swaps only the world and the judge:

  * world  = a realized `RegisterWorld` (an instance of a calibrated `LinkSpec`), probed through
             an in-process `RegisterChannel` (cells, not WILT booleans).
  * judge  = band-normalized **coverage** (how many of the M hidden cells the agent reconstructs
             correctly), normalized into the model-free floor->oracle band. Outcome-only,
             agent-inaccessible, deterministic — the integrity floor, lifted to coverage.

There is no world-smith yet: the curriculum is a single calibrated spec, and "worlds" are
fresh register draws of it (a different hidden world each, same public structure). Train and a
disjoint held-out set are both instances of that spec, so held-out coverage measures
generalization across unseen *instances* — the honest first-loop analog while the curriculum is
one calibrated world. References are spec-constant, so the band is the same for both splits.

One iteration mirrors `hta/loop.py`: seed gen_0000 if empty -> select a parent -> draw this
iteration's worlds -> eval the PARENT (baseline) -> meta agent branches + self-modifies it into
a CHILD -> eval the CHILD on the SAME worlds -> score (train + held-out) -> archive -> report
whether the child improved.
"""

import os
import random
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from .. import meta_agent, taste
from ..archive import Archive
from ..config import Config
from ..task_agent import load_solver
from . import register_world as rw
from .threshold import LinkSpec

SEED_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "seed_ch2")
SOLVED_BAR = 0.85   # norm at/above which a world counts as "reached the oracle" (the band ceiling)

# The meta-agent instruction for Chapter 2 (the harness contract differs from Chapter 1's). Filled
# with the editable meta_strategy.md and passed to the shared meta_agent.self_modify.
META_INSTRUCTION = """You are the META AGENT in a self-improving research system (Chapter 2).

GOAL: improve the TASK AGENT so it uncovers more of an unknown world under a scarce probe budget
-- so it grows better *research taste*. You are NOT given a checklist of what good taste is, and
you must NOT assume one: read the agent's actual behavior and let the evidence tell you where its
investigation was weak. Diagnose from what happened, not from a template.

The task agent is a HARNESS. `solver.py` defines `class Solver` with `run(self, ctx) -> list[int]`
(a reconstruction, one color per cell). Through `ctx` the harness deploys claude-agent sessions
over the world and assembles the answer:
  - ctx.world_map()    -> public structure {M, K, R, budget, cells:[{index,coeffs,const,formula}]}
  - ctx.remaining()    -> probes left in the GLOBAL budget (shared across all agents)
  - ctx.observations() -> {cell_index: color} accumulated across every agent so far
  - ctx.run_agent(prompt, max_probes=..., max_turns=..., extra_tools=())
        -> {submission, observations, probes_used, result}; deploys ONE airgapped agent (tools:
           probe / remaining / submit_map) that may probe up to max_probes and optionally submit.
The ARCHITECTURE is yours to evolve: one agent or several, single-shot or decomposed by block,
what each agent is told, what is carried between them, and what Python does with the results
(e.g. once enough cells are probed the registers satisfy a small linear system you can solve in
Python, then compute every cell -- instead of asking a model to eyeball them). Probing always
goes through an agent (the airgap); computation is free Python.

You are in the task agent's own workspace. Files:
  - `solver.py`        : the editable harness program.
  - `meta_strategy.md` : YOUR editable playbook for how to improve the task agent.
  - `EVAL_REPORT.md`   : how the current harness behaved -- agents deployed, cells probed, the
                         reconstruction, and coverage. The hidden register values are NOT given and
                         you must not try to reconstruct them; reason only about the agent's conduct.

YOUR PLAYBOOK (meta_strategy.md) says:
---
{meta_strategy}
---

DO THIS:
1. Read EVAL_REPORT.md and solver.py.
2. From the trajectory and outcomes alone, infer the single most impactful weakness in how this
   harness investigates -- where did it waste budget or fail to determine cells it could have?
   Name the weakness you actually see; do not pattern-match.
3. Edit solver.py to fix it with the smallest general change -- prefer structure (how it allocates
   probes across agents, tracks what it knows, reconstructs the rest) over wording. Keep a valid
   Python file defining class Solver with run(self, ctx) -> list[int]; import no world internals;
   interact only via ctx. Keep the program short (favor fitness-per-bit).
4. If you found a better general improvement *procedure*, also improve meta_strategy.md.

Make concrete edits now. Do not ask questions."""


# ---------------------------------------------------------------------------
# Worlds: fresh register draws of one calibrated spec. Parent and child see the SAME draws
# (fair comparison); each iteration reseeds so the agent can't memorize specific instances.
# ---------------------------------------------------------------------------
def build_worlds(spec: LinkSpec, n_train: int, n_transfer: int, iteration: int):
    base = 10_000 * (iteration + 1)
    train = [rw.RegisterWorld(spec, base + i) for i in range(n_train)]
    transfer = [rw.RegisterWorld(spec, base + 5_000 + i) for i in range(n_transfer)]
    return train, transfer


# ---------------------------------------------------------------------------
# Run one episode: the editable harness (Solver.run) deploys agent session(s) over the world via
# the AgentContext and assembles a reconstruction; we score its coverage.
# ---------------------------------------------------------------------------
def _run_on_world(solver, world: rw.RegisterWorld, cfg: Config, log=print) -> dict:
    ctx = rw.AgentContext(world, cfg, log=log)
    recon = None
    try:
        recon = solver.run(ctx)
    except Exception as e:  # a broken child must score, not crash the loop
        log(f"  ch2 harness crashed on a world: {e}")
    return {"agent_calls": ctx.agent_calls, "observations": ctx.observations(),
            "recon": recon, "score": world.score(recon)}


def _aggregate_repeats(recs: List[dict]) -> dict:
    """Collapse N repeats of ONE world: average raw coverage (damping Haiku's variance), keep the
    first repeat's trajectory/recon for the qualitative report."""
    base = dict(recs[0])
    raw = sum(r["score"]["raw"] for r in recs) / len(recs)
    base["score"] = dict(recs[0]["score"])
    base["score"]["raw"] = round(raw, 4)
    return base


def evaluate(solver_dir: str, worlds: List[rw.RegisterWorld], cfg: Config, log=print) -> dict:
    """Evaluate a solver across worlds; return aggregate coverage + a SANITIZED report. Real
    episodes are independent (one Solver instance, stateless across run() calls), so (world x
    repeat) units run concurrently; mock stays serial and deterministic. Aggregation is
    norm-of-mean (average raw coverage, normalize ONCE) — run_slice's lesson that averaging
    per-episode normalized scores double-counts the [0,1] clamp."""
    if not worlds:
        return {"mean_raw": 0.0, "mean_norm": 0.0, "solved": 0, "n_worlds": 0,
                "per_world": [], "report_md": "# (no worlds)\n"}
    solver = load_solver(solver_dir)
    repeats = max(getattr(cfg, "eval_repeats", 1) or 1, 1)
    concurrency = max(getattr(cfg, "eval_concurrency", 1) or 1, 1)
    units = [i for i in range(len(worlds)) for _ in range(repeats)]
    recs_by_world: dict = {i: [] for i in range(len(worlds))}

    if cfg.backend == "mock" or concurrency <= 1 or len(units) <= 1:
        for i in units:
            recs_by_world[i].append(_run_on_world(solver, worlds[i], cfg, log=log))
    else:
        with ThreadPoolExecutor(max_workers=min(concurrency, len(units))) as ex:
            for i, rec in ex.map(lambda i: (i, _run_on_world(solver, worlds[i], cfg, log=log)),
                                 units):
                recs_by_world[i].append(rec)

    ref = worlds[0].ref  # spec-constant
    per_world = []
    for i, w in enumerate(worlds):
        recs = recs_by_world[i]
        rec = recs[0] if len(recs) == 1 else _aggregate_repeats(recs)
        # renormalize the (possibly averaged) raw into the band for per-world reporting
        rec["score"]["norm"] = rw.normalize(rec["score"]["raw"], ref)
        per_world.append(rec)
        s = rec["score"]
        log(f"  world_{i}: raw={s['raw']:.3f} norm={s['norm']:.2f} "
            f"correct={s['correct']}/{s['M']} valid={s['valid']}"
            + ("" if repeats == 1 else f" (avg of {repeats})"))

    mean_raw = sum(r["score"]["raw"] for r in per_world) / len(per_world)
    mean_norm = rw.normalize(mean_raw, ref)
    solved = sum(1 for r in per_world if r["score"]["norm"] >= SOLVED_BAR)
    return {"mean_raw": round(mean_raw, 4), "mean_norm": round(mean_norm, 4),
            "solved": solved, "n_worlds": len(worlds), "per_world": per_world,
            "report_md": _sanitized_report(per_world, worlds[0], ref)}


def _eval_split(solver_dir, train, transfer, cfg, log):
    log(" train worlds:")
    tr = evaluate(solver_dir, train, cfg, log=log)
    log(" held-out worlds (fresh instances):")
    te = evaluate(solver_dir, transfer, cfg, log=log)
    # combined fitness weights train and held-out equally -> improvement must generalize across
    # instances, not memorize the ones it trained on (Chapter 1's transfer discipline).
    combined = round((tr["mean_norm"] + te["mean_norm"]) / 2.0, 4)
    return {"train": tr, "transfer": te, "combined_fitness": combined}


# ---------------------------------------------------------------------------
# Sanitized report for the meta agent. Shows the harness's OWN conduct (how many agents it
# deployed, which cells they probed, what was observed, the reconstruction, the coverage) and the
# PUBLIC formulas — never the hidden register values or the true colors of un-probed cells. So the
# meta agent reasons about *how the agent investigated*, never about the answer.
# ---------------------------------------------------------------------------
def _sanitized_report(per_world: List[dict], world0: rw.RegisterWorld, ref: dict) -> str:
    spec = world0.spec
    lines = [
        "# Coverage evaluation report (sanitized)\n",
        f"The world: {spec.M} cells, each a KNOWN function of {spec.R} hidden registers "
        f"(values 0..{spec.K - 1} — the only hidden information). Per-cell formulas (public, "
        "the same across every world below):",
    ]
    lines += [f"  cell {i}: {rw._cell_formula(co, k, spec.K)}"
              for i, (co, k) in enumerate(spec.cells())]
    lines += [
        f"\nProbe budget per world: {spec.budget}. Coverage band (raw): floor "
        f"{ref['floor_raw']:.3f} -> oracle {ref['oracle_raw']:.3f}.",
        "You are NOT given the register values or the true colors of un-probed cells; reason only "
        "about the harness's CONDUCT — how many agents it deployed, which cells they probed, and "
        "whether the reconstruction used the public structure to predict the rest.\n",
    ]
    for i, r in enumerate(per_world):
        s, calls, obs = r["score"], r["agent_calls"], r["observations"]
        lines.append(f"\n## world_{i}")
        lines.append(f"- coverage: {s['raw']*100:.0f}% of cells correct "
                     f"({s['norm']:.2f} of the floor->oracle band); valid_submission={s['valid']}")
        lines.append(f"- agents deployed: {len(calls)}")
        for j, c in enumerate(calls):
            lines.append(f"    agent {j}: probed {c['probed']} ({c['probes_used']} of budget), "
                         f"submitted_map={c['submitted']}")
        obs_str = ", ".join(f"cell {k2}->{obs[k2]}" for k2 in sorted(obs)) or "(none)"
        lines.append(f"- cells observed (across all agents): {obs_str}")
        lines.append(f"- reconstruction submitted: {r['recon']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# One iteration.
# ---------------------------------------------------------------------------
def run_iteration(cfg: Config, spec: LinkSpec, iteration: int = 0, log=print) -> dict:
    archive = Archive(cfg.archive_dir)
    rng = random.Random(iteration)

    if archive.is_empty():
        archive.seed(SEED_DIR)
        log("seeded gen_0000 from ch2 seed program")

    parent = archive.select_parent(rng, policy=cfg.parent_selection,
                                   novelty_scale=cfg.parent_novelty_scale,
                                   sharpness=cfg.parent_quality_sharpness,
                                   mdl_lambda=cfg.mdl_lambda)
    parent_dir = archive.node_dir(parent)
    log(f"selected parent: gen_{parent:04d} (selection={cfg.parent_selection})")

    train, transfer = build_worlds(spec, cfg.n_train_worlds, cfg.n_transfer_worlds, iteration)
    log(f"world: {spec.name}  M={spec.M} K={spec.K} R={spec.R} budget={spec.budget}  "
        f"({len(train)} train + {len(transfer)} held-out instances)")

    log("\n[evaluate PARENT]")
    parent_eval = _eval_split(parent_dir, train, transfer, cfg, log=log)

    log("\n[meta agent: branch + self-modify]")
    genid = archive.next_genid()
    child_dir = archive.node_dir(genid)
    meta_agent.self_modify(parent_dir, child_dir,
                           report_md=parent_eval["train"]["report_md"], cfg=cfg, log=log,
                           instruction_template=META_INSTRUCTION)

    log("\n[evaluate CHILD]")
    try:
        child_eval = _eval_split(child_dir, train, transfer, cfg, log=log)
        valid = True
    except Exception as e:
        log(f"child failed to evaluate (invalid program): {e}")
        child_eval = {"train": {"mean_norm": 0.0, "solved": 0},
                      "transfer": {"mean_norm": 0.0, "solved": 0}, "combined_fitness": 0.0}
        valid = False

    try:
        with open(os.path.join(child_dir, "solver.py")) as f:
            program_size = taste.program_description_length(f.read())
    except OSError:
        program_size = None

    summary = {
        "fitness": child_eval["combined_fitness"],
        "train_fitness": child_eval["train"]["mean_norm"],
        "transfer_fitness": child_eval["transfer"]["mean_norm"],
        "solved_train": child_eval["train"]["solved"],
        "solved_transfer": child_eval["transfer"]["solved"],
        "valid": valid,
        "spec": spec.name,
        "program_size": program_size,
    }
    archive.add(genid, parent, summary)

    improved = child_eval["combined_fitness"] > parent_eval["combined_fitness"]
    return {
        "parent": parent, "child": genid,
        "parent_fitness": parent_eval["combined_fitness"],
        "child_fitness": child_eval["combined_fitness"],
        "improved": improved,
        "parent_norm": (parent_eval["train"]["mean_norm"], parent_eval["transfer"]["mean_norm"]),
        "child_norm": (child_eval["train"]["mean_norm"], child_eval["transfer"]["mean_norm"]),
        "valid_child": valid,
    }
