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
from ..task_agent import load_solver, _task_llm
from . import register_world as rw
from .threshold import LinkSpec

SEED_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "seed_ch2")
SOLVED_BAR = 0.85   # norm at/above which a world counts as "reached the oracle" (the band ceiling)


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
# Run one program-driven episode: the editable Solver orchestrates the probing through the
# in-process channel and reasons through the (stateless) task llm; we score its reconstruction.
# ---------------------------------------------------------------------------
def _run_on_world(solver, world: rw.RegisterWorld, cfg: Config, log=print) -> dict:
    channel = world.open_channel()
    llm_fn = _task_llm(cfg)
    recon = None
    try:
        recon = solver.run(channel, llm_fn)
    except Exception as e:  # a broken child must score, not crash the loop
        log(f"  ch2 solver crashed on a world: {e}")
    return {"history": channel.history(), "recon": recon, "score": world.score(recon)}


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
# Sanitized report for the meta agent. Shows the agent's OWN conduct (which cells it probed,
# what it observed, the reconstruction it submitted, the coverage it earned) and the PUBLIC
# formulas — never the hidden register values or the true colors of unprobed cells. So the meta
# agent reasons about *how the agent investigated*, never about the answer.
# ---------------------------------------------------------------------------
def _sanitized_report(per_world: List[dict], world0: rw.RegisterWorld, ref: dict) -> str:
    info = world0.open_channel().world_map()
    lines = [
        "# Coverage evaluation report (sanitized)\n",
        f"The world: {info['M']} cells, each a KNOWN function of {info['R']} hidden registers "
        f"(values 0..{info['K'] - 1} — the only hidden information). Per-cell formulas (public, "
        "the same across every world below):",
    ]
    lines += [f"  cell {c['index']}: {c['formula']}" for c in info["cells"]]
    lines += [
        f"\nProbe budget per world: {info['budget']}. Coverage band (raw): floor "
        f"{ref['floor_raw']:.3f} -> oracle {ref['oracle_raw']:.3f}.",
        "You are NOT given the register values or the true colors of cells the agent did not "
        "probe; reason only about the agent's CONDUCT — which cells it chose to probe, and "
        "whether its reconstruction used the public structure to predict the rest.\n",
    ]
    for i, r in enumerate(per_world):
        s = r["score"]
        used = [h for h in r["history"] if not h.get("malformed")]
        probes = "; ".join(f"cell {h['index']}->{h['value']}"
                           + ("[REPEAT]" if h.get("reused") else "") for h in used) or "(none)"
        bad = sum(1 for h in r["history"] if h.get("malformed"))
        lines.append(f"\n## world_{i}")
        lines.append(f"- coverage: {s['raw']*100:.0f}% of cells correct "
                     f"({s['norm']:.2f} of the floor->oracle band); valid_submission={s['valid']}")
        lines.append(f"- probes ({len(used)}/{info['budget']} used"
                     + (f", {bad} malformed" if bad else "") + f"): {probes}")
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
                           report_md=parent_eval["train"]["report_md"], cfg=cfg, log=log)

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
