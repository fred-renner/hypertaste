"""The bet, run end-to-end: race toggle-on against toggle-off and report the lift.

Two arms, same harness, same world variations -- the only difference is the
decision discipline (playbook vs baseline). For each seed and arm we run one
episode and read the objective DiscoveryWorld scores; then we report, per arm,
the path/process score, completion rate, and cost.

  python bet/run_bet.py                                  # offline mock (free, plumbing)
  python bet/run_bet.py --backend real --seeds 0,1,2     # the live two-arm race (Haiku)
  python bet/run_bet.py --backend real --scenario Proteomics --difficulty Normal \
        --seeds 0,1,2,3,4 --max-steps 40

The v1 gate (BET.md): does toggle-on beat toggle-off on held-out variations.
"""

import argparse
import json
import os
import time

import episode as ep

_HERE = os.path.dirname(os.path.abspath(__file__))


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else 0.0


def _summarize(results):
    by_arm = {}
    for r in results:
        sc = r.get("scorecard", {})
        a = by_arm.setdefault(r["arm"], {"process": [], "success": [], "cost": [], "steps": []})
        a["process"].append(sc.get("process_score"))
        a["success"].append(1.0 if sc.get("completed_successfully") else 0.0)
        a["cost"].append(r.get("agent", {}).get("cost_usd", 0.0))
        a["steps"].append(sc.get("steps_used"))
    return {arm: {
        "n": len(v["process"]),
        "process_score": round(_mean(v["process"]), 3),
        "success_rate": round(_mean(v["success"]), 3),
        "mean_cost_usd": round(_mean(v["cost"]), 4),
        "mean_steps": round(_mean(v["steps"]), 1),
    } for arm, v in by_arm.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="Proteomics")
    ap.add_argument("--difficulty", default="Normal")
    ap.add_argument("--seeds", default="0", help="comma-separated, e.g. 0,1,2")
    ap.add_argument("--arms", default="off,on", help="comma-separated subset of off,on")
    ap.add_argument("--backend", default="mock", choices=["mock", "real"])
    ap.add_argument("--max-steps", type=int, default=30)
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--out", default=os.path.join(_HERE, "results"))
    args = ap.parse_args()

    seeds = [int(s) for s in args.seeds.split(",") if s.strip() != ""]
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    os.makedirs(args.out, exist_ok=True)

    results = []
    thread_id = 1
    print(f"== bet: {args.scenario}/{args.difficulty} | arms={arms} | seeds={seeds} "
          f"| backend={args.backend} | budget={args.max_steps} ==\n")
    for seed in seeds:
        for arm in arms:
            t0 = time.time()
            r = ep.run_episode(arm, args.scenario, args.difficulty, seed,
                               backend=args.backend, max_steps=args.max_steps,
                               model=args.model, thread_id=thread_id)
            thread_id += 1
            sc = r["scorecard"]
            dt = time.time() - t0
            print(f"seed {seed} arm {arm:>3}: process={sc.get('process_score'):.3f} "
                  f"success={sc.get('completed_successfully')} "
                  f"steps={sc.get('steps_used')} "
                  f"cost=${r['agent'].get('cost_usd',0.0):.4f} ({dt:.0f}s)")
            results.append(r)

    summary = _summarize(results)
    print("\n== summary (per arm) ==")
    for arm in arms:
        s = summary.get(arm)
        if s:
            print(f"  {arm:>3}: process={s['process_score']:.3f} "
                  f"success={s['success_rate']:.3f} "
                  f"steps={s['mean_steps']} cost=${s['mean_cost_usd']:.4f} (n={s['n']})")
    if "on" in summary and "off" in summary:
        lift = summary["on"]["process_score"] - summary["off"]["process_score"]
        print(f"\n  LIFT (on - off) on process score: {lift:+.3f}")
        print("  v1 gate: toggle-on beats toggle-off on held-out variations.")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_path = os.path.join(args.out, f"bet-{args.backend}-{stamp}.json")
    with open(out_path, "w") as f:
        json.dump({"args": vars(args), "summary": summary, "results": results},
                  f, indent=2)
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
