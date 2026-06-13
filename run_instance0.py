#!/usr/bin/env python3
"""Instance 0 — the proof of principle for the **machine world** (kit v1; PLAN.md -> record v2,
"The proof of principle"; the settled picture in `PASS3_REDO.md`). The smallest honest slice of the
self-improving-taste loop on the new world:

  1. SCREEN (free, model-free, no LLM): build-screen the one hand-authored blueprint. Scripted QA
     probers (random pokes, sweep-and-fit, even-enumerate) must score ≈ 0 of the band, and a
     reference tasteful allocator must clear them — the proof a real taste gap exists for the loop
     to grow into. This is gate 1 ("too easy?"), QA on the world, not baselines for the agent.

  2. INNER LOOP (costs money, --backend real): author the best day-one playbook (Opus, blind), coach
     it from the student's conduct on train draws, then eval bare / day-one / coached on fresh
     held-out machines. The signal sought: COACHED > DAY-ONE on fresh worlds.

  python run_instance0.py                       # screen only (free)
  python run_instance0.py --backend mock        # + the inner-loop plumbing (deterministic, free)
  python run_instance0.py --backend real        # + the LIVE inner loop (a few dollars)
"""

import argparse
import json
import os

from hta import llm
from hta.config import Config
from hta.ch2 import machine_loop as ml
from hta.ch2 import machine_qa as qa

FLOOR_BAR = 0.25     # no scripted prober may exceed this fraction of the band (else "too easy")
GAP_BAR = 0.08       # the reference tasteful allocator must clear the scripted floor by at least this


def screen(seeds=range(120)) -> bool:
    bp = ml.instance0()
    print("=" * 92)
    print("1. SCREEN (model-free) — is the world too easy, and is there a real taste gap?")
    print("=" * 92)
    print(f"  blueprint '{bp.name}': {len(bp.slots)} outputs (domain,weight)={list(bp.slots)}")
    print(f"  budget {bp.budget}, p_affine {bp.p_affine}, p_const {bp.p_const}; "
          f"exam = full input domain of every output (sum {sum(d for d, _ in bp.slots)} ≫ budget)\n")
    r = qa.screen_blueprint(bp, seeds=seeds)
    for name in ("random_poke", "sweep_fit", "enumerate_even"):
        flag = "ok" if r[name] <= FLOOR_BAR else "TOO HIGH"
        print(f"  scripted  {name:<16} {r[name]:+.3f}n   [{flag}]")
    print(f"  --------\n  reference_tasteful        {r['reference_tasteful']:+.3f}n")
    print(f"  scripted floor            {r['scripted_floor']:+.3f}n")
    print(f"  taste gap (tasteful-floor) {r['gap']:+.3f}n")
    ok = r["scripted_floor"] <= FLOOR_BAR and r["gap"] >= GAP_BAR
    print(f"\n  GATE: scripted floor <= {FLOOR_BAR} and gap >= {GAP_BAR}  ->  {'PASS' if ok else 'FAIL'}")
    print("  (reference_tasteful is a model-free headroom check, NOT a runtime baseline — only the")
    print("   live student answers whether the world is in its ZPD; that is the inner loop below.)")
    return ok


def inner_loop(cfg: Config, args) -> None:
    print("\n" + "=" * 92)
    print(f"2. INNER LOOP ({'LIVE' if cfg.backend == 'real' else 'plumbing'}) — "
          f"bare vs day-one vs coached on fresh held-out machines")
    print("=" * 92)
    llm.reset_accounting()
    res = ml.run_instance0(cfg, n_train=args.n_train, n_holdout=args.n_holdout,
                           coaching_rounds=args.coaching_rounds, seed=args.seed)

    print("\n" + "=" * 92)
    print("RESULT — held-out mean band score (norm: 0 = lazy/all-abstain, 1 = perfect)")
    print("=" * 92)
    print(f"  bare student   : {res['bare_norm']:+.3f}n")
    print(f"  day-one (null) : {res['day_one_norm']:+.3f}n")
    print(f"  coached        : {res['coached_norm']:+.3f}n")
    print(f"  ------\n  coached - day-one : {res['gap_coached_minus_dayone']:+.3f}n  "
          f"<- the signal (positive = the grown playbook beats the best day-one playbook)")

    os.makedirs(cfg.out_dir, exist_ok=True)
    path = os.path.join(cfg.out_dir, "instance0.json")
    with open(path, "w") as f:
        json.dump(res, f, indent=2)
    print(f"\n  artifacts written to {path}")
    if cfg.backend == "real":
        acct = llm.accounting()
        print(f"  cost: {acct['calls']} claude -p calls, ${acct['cost_usd']:.4f}  by_role={acct['by_role']}")


def main():
    ap = argparse.ArgumentParser(description="Instance 0 — machine-world proof of principle")
    ap.add_argument("--backend", choices=["none", "mock", "real"], default="none",
                    help="none = screen only (free); mock = + plumbing; real = + the LIVE inner loop")
    ap.add_argument("--n-train", type=int, default=3, dest="n_train")
    ap.add_argument("--n-holdout", type=int, default=5, dest="n_holdout")
    ap.add_argument("--coaching-rounds", type=int, default=1, dest="coaching_rounds")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out-dir", default="outputs/instance0")
    args = ap.parse_args()

    ok = screen()
    if args.backend == "none":
        print("\n  (screen only; pass --backend real to run the LIVE inner loop)")
        return
    if not ok:
        print("\n  screen did not pass — not spending on the inner loop. Reshape the blueprint first.")
        return

    cfg = Config()
    cfg.backend = args.backend
    cfg.out_dir = args.out_dir
    inner_loop(cfg, args)


if __name__ == "__main__":
    main()
