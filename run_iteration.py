#!/usr/bin/env python3
"""Run ONE DGM-H iteration end-to-end and report whether the child improved.

Examples:
    python run_iteration.py                      # mock backend, testing profile
    python run_iteration.py --backend real       # real claude -p (Haiku task, Opus meta/world)
    python run_iteration.py --backend real --meta-model haiku   # cheaper smoke
"""

import argparse

from hta import llm
from hta.config import Config
from hta import loop


def add_common_args(ap: argparse.ArgumentParser) -> None:
    """The run knobs shared by run_iteration.py and run_loop.py (single source so the
    two launchers can't drift). run_loop adds its own --iterations on top."""
    ap.add_argument("--backend", choices=["mock", "real"])
    ap.add_argument("--profile", choices=["testing", "full"], default="testing")
    ap.add_argument("--task-model", dest="task_model")
    ap.add_argument("--meta-model", dest="meta_model")
    ap.add_argument("--world-model", dest="world_model")
    ap.add_argument("--max-probes", dest="max_probes", type=int)
    ap.add_argument("--episode-mode", dest="episode_mode",
                    choices=["per_probe", "single_session"])
    ap.add_argument("--n-train", dest="n_train", type=int)
    ap.add_argument("--n-transfer", dest="n_transfer", type=int)
    ap.add_argument("--meta-max-turns", dest="meta_max_turns", type=int)
    ap.add_argument("--eval-repeats", dest="eval_repeats", type=int,
                    help="run each world's episode N times and average (variance damping)")
    ap.add_argument("--eval-concurrency", dest="eval_concurrency", type=int,
                    help="max simultaneous claude -p episodes (real backend; speed)")
    ap.add_argument("--parent-selection", dest="parent_selection",
                    choices=["weighted", "random"],
                    help="archive parent policy: weighted quality x novelty | uniform random")
    ap.add_argument("--sandbox", choices=["none", "docker"],
                    help="meta-agent airgap: none (Bash-denied, in-process) | "
                         "docker (host-isolated container). docker fails closed.")
    ap.add_argument("--out-dir", dest="out_dir")


def build_config(args) -> Config:
    cfg = Config.testing() if args.profile == "testing" else Config()
    if args.backend:
        cfg.backend = args.backend
    if args.task_model:
        cfg.task_model = args.task_model
    if args.meta_model:
        cfg.meta_model = args.meta_model
    if args.world_model:
        cfg.world_model = args.world_model
    if args.max_probes is not None:
        cfg.max_probes = args.max_probes
    if getattr(args, "episode_mode", None):
        cfg.episode_mode = args.episode_mode
    if getattr(args, "n_train", None) is not None:
        cfg.n_train_worlds = args.n_train
    if getattr(args, "n_transfer", None) is not None:
        cfg.n_transfer_worlds = args.n_transfer
    if getattr(args, "meta_max_turns", None) is not None:
        cfg.meta_max_turns = args.meta_max_turns
    if getattr(args, "eval_repeats", None) is not None:
        cfg.eval_repeats = args.eval_repeats
    if getattr(args, "eval_concurrency", None) is not None:
        cfg.eval_concurrency = args.eval_concurrency
    if getattr(args, "parent_selection", None):
        cfg.parent_selection = args.parent_selection
    if getattr(args, "sandbox", None):
        cfg.sandbox = args.sandbox
    if args.out_dir:
        cfg.out_dir = args.out_dir
    return cfg


def main():
    ap = argparse.ArgumentParser()
    add_common_args(ap)
    args = ap.parse_args()

    cfg = build_config(args)
    llm.reset_accounting()

    print("=" * 70)
    print(f"hypertaste :: one iteration  [backend={cfg.backend}, profile={args.profile}]")
    print(f"models: task={cfg.task_model}  meta={cfg.meta_model}  world={cfg.world_model}")
    print(f"episode_mode: {cfg.episode_mode}   meta-sandbox: {cfg.sandbox}")
    print(f"knobs:  max_probes={cfg.max_probes}  train={cfg.n_train_worlds}  "
          f"transfer={cfg.n_transfer_worlds}")
    print("=" * 70)

    report = loop.run_iteration(cfg)

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"parent gen_{report['parent']:04d}  fitness={report['parent_fitness']:.4f}  "
          f"solved(train,transfer)={report['parent_solved']}")
    print(f"child  gen_{report['child']:04d}  fitness={report['child_fitness']:.4f}  "
          f"solved(train,transfer)={report['child_solved']}")
    print(f"valid child program: {report['valid_child']}")
    delta = report['child_fitness'] - report['parent_fitness']
    verdict = "IMPROVED" if report["improved"] else ("REGRESSED" if delta < 0 else "no change")
    print(f"\n>>> {verdict}  (Δfitness = {delta:+.4f})")

    acct = llm.accounting()
    print(f"\nLLM calls: {acct['calls']}  est_cost=${acct['cost_usd']}  "
          f"by_role={acct['by_role']}")


if __name__ == "__main__":
    main()
