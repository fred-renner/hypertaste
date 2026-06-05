#!/usr/bin/env python3
"""Run N DGM-H iterations and print the fitness progression / best stepping stone.

    python run_loop.py --iterations 5            # mock
    python run_loop.py --iterations 3 --backend real
"""

import argparse

from hta import llm
from hta.archive import Archive
from hta import loop
from run_iteration import add_common_args, build_config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=3)
    add_common_args(ap)
    args = ap.parse_args()

    cfg = build_config(args)
    llm.reset_accounting()
    print(f"Running {args.iterations} iterations [backend={cfg.backend}] ...\n")

    history = []
    for i in range(args.iterations):
        print(f"\n########## ITERATION {i + 1}/{args.iterations} ##########")
        rep = loop.run_iteration(cfg, seed=i)
        history.append(rep)
        print(f"  -> gen_{rep['child']:04d} fitness={rep['child_fitness']:.4f} "
              f"(parent gen_{rep['parent']:04d}={rep['parent_fitness']:.4f}) "
              f"{'IMPROVED' if rep['improved'] else ''}")

    arch = Archive(cfg.archive_dir)
    best = arch.best()
    print("\n" + "=" * 70)
    # Four curves, not one: the composite is solve-dominated and can sit flat while the
    # agent's taste genuinely improves. Reading solve-rate, the HELD-OUT transfer
    # solve-rate (the honest "is it really learning" signal), and info-gain separately
    # tells "agent got better" apart from "score moved".
    def curve(fn):
        return " -> ".join(fn(h) for h in history)
    print("PROGRESSION (per iteration):")
    print("  composite fitness : " + curve(lambda h: f"{h['child_fitness']:.3f}"))
    print("  solve-rate (all)  : " + curve(lambda h: f"{h['components']['solve_rate']:.2f}"))
    print("  transfer-solve    : " + curve(
        lambda h: f"{(h['child_solved'][1] / (h['n_transfer'] or 1)):.2f}"))
    print("  info-gain (taste) : " + curve(lambda h: f"{h['components']['avg_info_gain']:.2f}"))
    print("  target_difficulty : " + curve(lambda h: f"{h['target_difficulty']}"))
    if best is not None:
        print(f"best stepping stone: gen_{best:04d} fitness={arch.fitness(best):.4f}")
    acct = llm.accounting()
    print(f"LLM calls: {acct['calls']}  est_cost=${acct['cost_usd']}  by_role={acct['by_role']}")


if __name__ == "__main__":
    main()
