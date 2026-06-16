#!/usr/bin/env python3
"""Drive the fresh lab — the world language + the two loops, built from DESIGN.md. One entry point
with three subcommands (the trail reference's run_anchor/run_loop/run_worldsmith, lifted onto the
world language):

  python run_lab.py screen                              # build-screen instance 0 + named worlds: free,
                                                        #   model-free, deterministic (the gate)
  python run_lab.py loop --iterations 1 --backend mock  # LOOP 1, offline (deterministic floor-player)
  python run_lab.py loop --iterations 1 --backend real  # LOOP 1, live (cents/Haiku episode, ~$1/Opus)
  python run_lab.py smith                               # LOOP 2 ship-gate (free, model-free)
  python run_lab.py smith --backend real                # + the LIVE closed-loop demonstration (~$2.5)

The `real` backend uses the host's authenticated `claude` CLI (subscription, no API key). The
runtime is stdlib-only (Python 3.11).
"""

import argparse

from hta import llm
from hta.config import Config
from hta.world import grade
from hta.world.instances import instance0, ladder_world, single_chain_world

MARGIN, CLIFF, HEUR_LO, HEUR_HI = 0.15, 0.55, 0.15, 0.80


def _fmt(s):
    return (f"{s['name']:<14} H={s['n_hyps']:>5} B={s['budget']} Lv={s['Lv']:>2} "
            f"| floor {s['floor']:>4.1f} heur {s['best_heur']:>5.2f} oracle {s['oracle']:>5.2f} "
            f"| gap {s['gap_raw']:>4.2f} ({s['gap_norm']:>5.2f}n) heur_n {s['heur_norm']:>5.2f} "
            f"maxstep {s['ramp_maxstep']:>4.2f}")


def cmd_screen(args):
    print("=" * 110)
    print("BUILD-SCREEN — the world language's worked instances (model-free; oracle ≫ heuristic gate)")
    print("=" * 110)
    print("Each world is a parts-list in the language (hta/world/language.py); the oracle/floor/screen")
    print("are re-derived mechanically (hta/world/grade.py). A world is ABOVE threshold when the")
    print("belief-MDP oracle strictly beats every generic planner (incl. 2-step lookahead).\n")
    for f in (single_chain_world, instance0, ladder_world):
        s = grade.screen(f(), clair=False)
        flags = []
        if s["gap_norm"] >= MARGIN:
            flags.append("THRESH")
        if s["ramp_monotone"] and s["ramp_maxstep"] <= CLIFF:
            flags.append("RAMP")
        if HEUR_LO <= s["heur_norm"] <= HEUR_HI:
            flags.append("ROOM")
        print(f"  {_fmt(s)}  {' '.join(flags)}")
        print("      basket: " + "  ".join(f"{k}={v:.2f}" for k, v in s["heurs"].items())
              + "  -> none reaches the oracle = the optimal allocation is not a shallow rule")
    print("\ninstance0 is the proof-of-principle world: a fork with a real gate and a deep valley plus")
    print("off-trail clearings — a POSITION worth reading (scout which chain is live before committing).")


def cmd_loop(args):
    from hta.dgmh import loop
    cfg = Config()
    cfg.backend = args.backend
    cfg.out_dir = args.out_dir
    cfg.n_train_worlds = args.n_train
    cfg.n_transfer_worlds = args.n_transfer
    cfg.eval_repeats = max(1, args.eval_repeats)
    if args.task_model:
        cfg.task_model = args.task_model
    if args.sandbox:
        cfg.sandbox = args.sandbox
    spec = instance0()

    llm.reset_accounting()
    print(f"== DGM-H loop (LOOP 1) on '{spec.name}' ==  backend={cfg.backend} "
          f"iterations={args.iterations} archive={cfg.archive_dir}")
    history = []
    for it in range(args.iterations):
        print("\n" + "=" * 72)
        print(f"ITERATION {it + 1}/{args.iterations}")
        print("=" * 72)
        rep = loop.run_iteration(cfg, iteration=it, spec=spec)
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
    run_path = loop.persist_run(cfg, vars(args), history, acct)
    print(f"artifacts: {run_path} (+ per-iteration iter_*.json, archive/)")


def cmd_smith(args):
    from hta.dgmh.archive import Archive
    from hta.dgmh import loop
    from hta.gym import smith
    cfg = Config()
    cfg.backend = args.backend
    cfg.out_dir = args.out_dir
    if args.sandbox:
        cfg.sandbox = args.sandbox

    print("=" * 100)
    print("WORLD-SMITH (LOOP 2) — ship-gate the curriculum's structural moves (model-free)")
    print("=" * 100)
    for mv in smith.CURRICULUM:
        spec = mv["spec"]()
        g = smith.ship_gate(spec, champion_method=mv["champion"], fix_method=mv["fix"])
        print(f"\n# {mv['label']}")
        print(f"  ship-gate '{spec.name}': gap {g['gap_norm']:.2f}n  champion {g['champion_norm']:.2f}n"
              f"  fix {g['fix_norm']:.2f}n  hard={g['hard']} solvable={g['solvable']} "
              f"champion_fails={g['champion_fails']}  ==> {'SHIP' if g['ship'] else 'HOLD'}")

    if args.backend != "real":
        print("\n(model-free ship-gate only; pass --backend real for the LIVE closed-loop demonstration)")
        return

    # Live: grow a champion on instance0 for one iteration, then run the curriculum from it.
    llm.reset_accounting()
    print("\n[grow a champion on instance0 for one iteration, then run the curriculum from it]")
    loop.run_iteration(cfg, iteration=0, spec=instance0())
    champion = Archive(cfg.archive_dir).best()
    champion_dir = Archive(cfg.archive_dir).node_dir(champion)
    smith.run_curriculum(champion_dir, cfg, n_eval=args.n_eval)
    acct = llm.accounting()
    print(f"\ncost: {acct['calls']} claude -p calls, ${acct['cost_usd']:.4f}  by_role={acct['by_role']}")


def main():
    ap = argparse.ArgumentParser(description="Drive the fresh lab (world language + the two loops)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("screen", help="build-screen the worked instances (free, model-free)")

    lp = sub.add_parser("loop", help="LOOP 1 — grow the agent on instance 0")
    lp.add_argument("--iterations", type=int, default=1)
    lp.add_argument("--backend", choices=["mock", "real"], default="mock")
    lp.add_argument("--n-train", dest="n_train", type=int, default=2)
    lp.add_argument("--n-transfer", dest="n_transfer", type=int, default=1)
    lp.add_argument("--eval-repeats", dest="eval_repeats", type=int, default=1)
    lp.add_argument("--task-model", dest="task_model", default=None)
    lp.add_argument("--sandbox", choices=["none", "docker"], default=None)
    lp.add_argument("--out-dir", dest="out_dir", default="outputs/lab")

    sm = sub.add_parser("smith", help="LOOP 2 — ship-gate the curriculum (+ live demo with --backend real)")
    sm.add_argument("--backend", choices=["mock", "real"], default="mock")
    sm.add_argument("--n-eval", dest="n_eval", type=int, default=4)
    sm.add_argument("--sandbox", choices=["none", "docker"], default=None)
    sm.add_argument("--out-dir", dest="out_dir", default="outputs/lab")

    args = ap.parse_args()
    {"screen": cmd_screen, "loop": cmd_loop, "smith": cmd_smith}[args.cmd](args)


if __name__ == "__main__":
    main()
