#!/usr/bin/env python3
"""Run the Chapter-2 **model-orchestrated** loop (option B) on the anchor trail world.

The reseed's loop (RESET_DESIGN.md -> "Next actions" 3-4): the seed is the floor playbook
(`hta/ch2/seed/playbook.md`) and the loop searches playbook-space — Opus rewrites the agent's
English *playbook*, a Haiku TOP session runs every episode through the confined probe-MCP airgap
(probe / spawn / mem / submit), and the judge is band-normalized coverage on the anchor family.

  python run_loop.py --iterations 1 --backend mock                 # free, deterministic plumbing
  python run_loop.py --iterations 1 --backend real --n-train 2 --n-transfer 1
  python run_loop.py --iterations 3 --backend real --sandbox docker --eval-repeats 2

Cost per real iteration ~= (n_train + n_transfer) * eval_repeats Haiku episodes (cents each, plus
any workers they spawn) + one Opus playbook rewrite (~$1, the dominant term). Step 4 is to CALIBRATE
live so Haiku lands in-band before scaling the iteration count; keep the eval lean until then.
"""

import argparse

from hta import llm
from hta.config import Config
from hta.ch2 import loop as ch2_loop


def main():
    ap = argparse.ArgumentParser(description="Chapter-2 model-orchestrated loop (anchor trail world)")
    ap.add_argument("--iterations", type=int, default=1)
    ap.add_argument("--backend", choices=["mock", "real"], default="mock")
    ap.add_argument("--n-train", type=int, default=2, help="train draws per iteration")
    ap.add_argument("--n-transfer", type=int, default=1, help="held-out draws per iteration")
    ap.add_argument("--eval-repeats", type=int, default=1, help="episodes per world (damps variance)")
    ap.add_argument("--task-model", default=None)
    ap.add_argument("--meta-model", default=None)
    ap.add_argument("--meta-max-turns", type=int, default=None)
    ap.add_argument("--sandbox", choices=["none", "docker"], default=None)
    ap.add_argument("--out-dir", default="outputs/ch2b", help="archive lives under <out-dir>/archive")
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

    llm.reset_accounting()
    print(f"== Chapter-2 model-orchestrated loop (anchor) ==  backend={cfg.backend} "
          f"iterations={args.iterations} archive={cfg.archive_dir}")

    history = []
    for it in range(args.iterations):
        print("\n" + "=" * 72)
        print(f"ITERATION {it + 1}/{args.iterations}")
        print("=" * 72)
        rep = ch2_loop.run_iteration(cfg, iteration=it)
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
