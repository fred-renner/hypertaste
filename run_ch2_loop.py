#!/usr/bin/env python3
"""Run the Chapter-2 meta-agent-on-program loop on a calibrated register world.

This is the loop CLAUDE.md -> "Next action" names: the seed is a blank slate (`hta/seed_ch2/`)
and the loop searches scaffold-space — Opus rewrites the task agent's *program* (how it
allocates probes, tracks the registers, reconstructs), Haiku runs every episode, and the judge
is band-normalized coverage on `trap-tetra` (the world live-calibrated into the ZPD). The
calibration is done in its own session; keep this eval lean (cost floor ~$0.11/episode).

  python run_ch2_loop.py --iterations 3 --backend mock                 # free, deterministic
  python run_ch2_loop.py --iterations 3 --backend real --n-train 2 --n-transfer 1
  python run_ch2_loop.py --iterations 3 --backend real --spec trap-tetra --eval-repeats 2

Cost per real iteration ~= (n_train + n_transfer) * eval_repeats * 2 agents Haiku episodes
+ one Opus meta edit (~$1, the dominant term). Start small; raise episode count only behind a
staged gate.
"""

import argparse

from hta import llm
from hta.config import Config
from hta.ch2 import loop as ch2_loop
from hta.ch2.threshold import LinkSpec
from run_threshold import candidates


def _spec(name: str) -> LinkSpec:
    for s in candidates():
        if s.name == name:
            return s
    raise SystemExit(f"unknown spec {name!r}; choices: {[s.name for s in candidates()]}")


def main():
    ap = argparse.ArgumentParser(description="Chapter-2 meta-agent-on-program loop (register world)")
    ap.add_argument("--iterations", type=int, default=3)
    ap.add_argument("--backend", choices=["mock", "real"], default="mock")
    ap.add_argument("--spec", default="trap-tetra", help="calibrated world (a threshold candidate)")
    ap.add_argument("--n-train", type=int, default=2, help="train instances per iteration")
    ap.add_argument("--n-transfer", type=int, default=1, help="held-out instances per iteration")
    ap.add_argument("--eval-repeats", type=int, default=1, help="episodes per world (damps variance)")
    ap.add_argument("--task-model", default=None)
    ap.add_argument("--meta-model", default=None)
    ap.add_argument("--meta-max-turns", type=int, default=None)
    ap.add_argument("--sandbox", choices=["none", "docker"], default=None)
    ap.add_argument("--out-dir", default="outputs/ch2", help="archive lives under <out-dir>/archive")
    args = ap.parse_args()

    cfg = Config()
    cfg.backend = args.backend
    cfg.out_dir = args.out_dir
    cfg.n_train_worlds = args.n_train
    cfg.n_transfer_worlds = args.n_transfer
    cfg.eval_repeats = max(1, args.eval_repeats)
    if args.task_model:
        cfg.task_model = args.task_model
    if args.meta_model:
        cfg.meta_model = args.meta_model
    if args.meta_max_turns is not None:
        cfg.meta_max_turns = args.meta_max_turns
    if args.sandbox:
        cfg.sandbox = args.sandbox

    spec = _spec(args.spec)
    llm.reset_accounting()
    print(f"== Chapter-2 loop on {spec.name} ==  backend={cfg.backend} "
          f"iterations={args.iterations} archive={cfg.archive_dir}")

    history = []
    for it in range(args.iterations):
        print("\n" + "=" * 72)
        print(f"ITERATION {it + 1}/{args.iterations}")
        print("=" * 72)
        rep = ch2_loop.run_iteration(cfg, spec, iteration=it)
        history.append(rep)
        flag = "improved" if rep["improved"] else "no improvement"
        print(f"\n-> gen_{rep['parent']:04d} (fit {rep['parent_fitness']:.3f}) "
              f"-> gen_{rep['child']:04d} (fit {rep['child_fitness']:.3f})  [{flag}]"
              + ("" if rep["valid_child"] else "  [INVALID CHILD]"))

    print("\n" + "=" * 72)
    print("PROGRESSION (combined train+held-out coverage, normalized into the band)")
    for it, rep in enumerate(history):
        print(f"  iter {it + 1}: gen_{rep['child']:04d}  fitness={rep['child_fitness']:.3f}  "
              f"train_norm={rep['child_norm'][0]:.2f} heldout_norm={rep['child_norm'][1]:.2f}")
    acct = llm.accounting()
    print(f"\ncost: {acct['calls']} claude -p calls, ${acct['cost_usd']:.4f}  by_role={acct['by_role']}")


if __name__ == "__main__":
    main()
