"""The DGM-H open-ended loop, one iteration at a time.

One iteration:
  1. seed gen_0 from the seed program if the archive is empty
  2. select a parent from the archive (open-ended: random among valid)
  3. world-smith builds training worlds (curriculum) + frozen transfer worlds
  4. evaluate the PARENT on those worlds (baseline)
  5. meta agent branches the parent and self-modifies it -> CHILD
  6. evaluate the CHILD on the same worlds
  7. score fitness (train + transfer), add child to the archive
  8. report whether the child improved over the parent

Parent and child are evaluated on the *same* world set so "did it improve" is a fair
comparison. Transfer worlds (frozen, never adapted by the smith) measure whether the
improvement is general research taste rather than overfitting to the curriculum.
"""

import os
import random
import shutil
from typing import Optional

from . import meta_agent, task_agent
from .archive import Archive
from .config import Config
from .world import world_smith

SEED_DIR = os.path.join(os.path.dirname(__file__), "seed")


def _frontier(archive: Archive):
    """Return (human summary, weak_tags) for the current best stepping stone."""
    b = archive.best()
    if b is None:
        return None, []
    m = archive._meta(b)
    weak = m.get("weak_tags", []) or []
    summary = (f"best fitness so far={m.get('fitness')}, "
               f"train_solved={m.get('solved_train')}, transfer_solved={m.get('solved_transfer')}, "
               f"weak_modes={m.get('weakness', [])}")
    return summary, weak


def _target_difficulty(archive: Archive, cfg: Config) -> int:
    """Zone-of-proximal-development: keep the curriculum just above current ability.
    Escalate when the best agent solves most worlds, ease off when it's struggling."""
    b = archive.best()
    if b is None:
        return 2  # no evaluated agent yet -> start moderate
    m = archive._meta(b)
    n = (cfg.n_train_worlds + cfg.n_transfer_worlds) or 1
    solved = (m.get("solved_train", 0) or 0) + (m.get("solved_transfer", 0) or 0)
    frac = solved / n
    base = m.get("target_difficulty", 2) or 2
    if frac >= 0.75:
        return min(base + 1, 5)
    if frac <= 0.25:
        return max(base - 1, 1)
    return base


def _eval_split(solver_dir, train_worlds, transfer_worlds, cfg, log):
    log(" train worlds:")
    tr = task_agent.evaluate(solver_dir, train_worlds, cfg, log=log)
    log(" transfer worlds (held-out):")
    te = task_agent.evaluate(solver_dir, transfer_worlds, cfg, log=log)
    # combined fitness weights train and transfer equally
    combined = round((tr["mean_fitness"] + te["mean_fitness"]) / 2.0, 4)
    # weakness profile across BOTH splits -> next iteration's curriculum target
    all_worlds = list(train_worlds) + list(transfer_worlds)
    all_pw = tr["per_world"] + te["per_world"]
    return {"train": tr, "transfer": te, "combined_fitness": combined,
            "weak_tags": task_agent.weak_tags(all_worlds, all_pw),
            "weakness": task_agent.weakness_flags(all_pw)}


def run_iteration(cfg: Config, seed: int = 0, log=print) -> dict:
    archive = Archive(cfg.archive_dir)
    rng = random.Random(seed)

    if archive.is_empty():
        archive.seed(SEED_DIR)
        log("seeded gen_0000 from seed program")

    parent = archive.select_parent(rng)
    parent_dir = archive.node_dir(parent)
    log(f"selected parent: gen_{parent:04d}")

    target_diff = _target_difficulty(archive, cfg)
    frontier_str, weak_tags = _frontier(archive)
    if weak_tags:
        log(f"curriculum: target_difficulty={target_diff}, targeting weak modes {weak_tags}")
    else:
        log(f"curriculum: target_difficulty={target_diff}")
    train_worlds = world_smith.build_worlds(cfg, target_difficulty=target_diff,
                                            weak_tags=weak_tags, frontier=frontier_str, log=log)
    transfer_worlds = world_smith.transfer_suite(cfg)

    log("\n[evaluate PARENT]")
    parent_eval = _eval_split(parent_dir, train_worlds, transfer_worlds, cfg, log=log)

    log("\n[meta agent: branch + self-modify]")
    genid = archive.next_genid()
    child_dir = archive.node_dir(genid)
    meta_agent.self_modify(parent_dir, child_dir,
                           report_md=parent_eval["train"]["report_md"], cfg=cfg, log=log)

    log("\n[evaluate CHILD]")
    try:
        child_eval = _eval_split(child_dir, train_worlds, transfer_worlds, cfg, log=log)
        valid = True
    except Exception as e:
        log(f"child failed to evaluate (invalid program): {e}")
        child_eval = {"train": {"mean_fitness": 0.0, "solved": 0},
                      "transfer": {"mean_fitness": 0.0, "solved": 0},
                      "combined_fitness": 0.0}
        valid = False

    summary = {
        "fitness": child_eval["combined_fitness"],
        "train_fitness": child_eval["train"]["mean_fitness"],
        "transfer_fitness": child_eval["transfer"]["mean_fitness"],
        "solved_train": child_eval["train"]["solved"],
        "solved_transfer": child_eval["transfer"]["solved"],
        "valid": valid,
        "target_difficulty": target_diff,
        "weak_tags": child_eval.get("weak_tags", []),
        "weakness": child_eval.get("weakness", []),
    }
    archive.add(genid, parent, summary)

    improved = child_eval["combined_fitness"] > parent_eval["combined_fitness"]
    report = {
        "parent": parent,
        "child": genid,
        "parent_fitness": parent_eval["combined_fitness"],
        "child_fitness": child_eval["combined_fitness"],
        "improved": improved,
        "parent_solved": (parent_eval["train"]["solved"], parent_eval["transfer"]["solved"]),
        "child_solved": (child_eval["train"]["solved"], child_eval["transfer"]["solved"]),
        "valid_child": valid,
    }
    return report
