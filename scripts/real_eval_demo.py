#!/usr/bin/env python3
"""Real-backend demo: run the task agent (Haiku, via constrained `claude -p`) on a
single airgapped WILT world, comparing the seed 'naive' strategy against a 'smart'
one. This isolates and captures the constrained-Haiku -> world -> objective-scoring
path (no meta agent, no evolution) so you can see live research-taste behavior cheaply.

    python scripts/real_eval_demo.py                      # strict_increasing, 5 probes
    python scripts/real_eval_demo.py --rule sum_eq --max-probes 8
    python scripts/real_eval_demo.py --strategies smart   # just the smart one

Requires the `claude` CLI installed and authenticated. ~ (max_probes+1) Haiku calls
per strategy.
"""

import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hta import llm, task_agent
from hta.config import Config
from hta.world.engine import WiltWorld
from hta.world.grammar import candidate_library

SEED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hta", "seed")


def run_strategy(strategy: str, world: WiltWorld, cfg: Config) -> dict:
    work = os.path.join("/tmp", f"hta_real_demo_{strategy}")
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(SEED_DIR, work)
    p = os.path.join(work, "solver.py")
    with open(p) as f:
        src = f.read()
    with open(p, "w") as f:
        f.write(src.replace('STRATEGY = "naive"', f'STRATEGY = "{strategy}"'))
    solver = task_agent.load_solver(work)
    print(f"\n--- REAL Haiku solver [{strategy}] ---", flush=True)
    rec = task_agent.run_on_world(solver, world, cfg, log=lambda m: print(m, flush=True))
    m = rec["metrics"]
    print(f"[{strategy}] trajectory:", flush=True)
    for h in rec["history"]:
        t = tuple(h["triple"]) if h["triple"] else "(malformed)"
        print(f"    {t} -> {h['label']}", flush=True)
    print(f"[{strategy}] guess = {rec['guess']!r}", flush=True)
    print(f"[{strategy}] solved={m['solved']} agreement={m['agreement']:.2f} "
          f"novelty={m['novelty']:.2f} infogain={m['avg_info_gain']:.2f} "
          f"fitness={m['fitness']:.3f}", flush=True)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", default="strict_increasing",
                    help="candidate-library rule name to use as the hidden world")
    ap.add_argument("--max-probes", type=int, default=5)
    ap.add_argument("--strategies", nargs="+", default=["naive", "smart"])
    ap.add_argument("--task-model", default="haiku")
    args = ap.parse_args()

    cfg = Config()
    cfg.backend = "real"
    cfg.max_probes = args.max_probes
    cfg.task_model = args.task_model
    llm.reset_accounting()

    rules = {r.name: r for r in candidate_library()}
    if args.rule not in rules:
        sys.exit(f"unknown rule {args.rule!r}; choices: {', '.join(sorted(rules))}")
    rule = rules[args.rule]
    print(f"HIDDEN RULE (our eyes only; NEVER shown to the agent): {rule.source}", flush=True)

    world = WiltWorld(rule, max_probes=cfg.max_probes)
    results = {s: run_strategy(s, world, cfg) for s in args.strategies}

    print("\n==================== REAL RESULT ====================", flush=True)
    for s, m in results.items():
        print(f"{s:>6}: fitness={m['fitness']:.3f} solved={m['solved']} "
              f"agreement={m['agreement']:.2f}", flush=True)
    print("accounting:", llm.accounting(), flush=True)


if __name__ == "__main__":
    main()
