#!/usr/bin/env python3
"""The WORLD-SMITH — the second loop's first deliverable: the **closed-loop demonstration**
(ROADMAP.md -> "The two loops"; RESET_DESIGN.md -> the integrity wall lifted to the world-smith).

The first loop proved the player can be coached to a world's edge (seed -> gen_0001, held-out
0.50 -> 1.00). `run_probe.py` then showed no *scalar* crank of the anchor re-opens a gap — the
champion's "commit to the deepest chain" survives every dial. So the gradient lives in the world's
STRUCTURE. This builds the curriculum half that evolves that structure, and demonstrates the loop:

  1. SHIP-GATE (model-free, free, deterministic). The world-smith authors a structurally harder world
     — the FORKED trail (`worlds.decoy_spec`): two candidate chains and a GATE whose hidden value says
     which is live, so committing to a chain without the cheap gate scout pins zero valley. The
     harness re-derives the oracle + coverage MECHANICALLY and ships the world only if it is HARD
     (oracle >> every generic planner), SOLVABLE (a reachable method reaches the oracle), and in the
     ZPD (the CHAMPION's method fails while the new method succeeds — fail-now-but-learnable). A
     no-fork control (above threshold, the champion still wins) shows the FORK is what breaks it.

  2. CLOSED LOOP (live, `--backend real`, ~$1 for the Opus coaching round + cents of Haiku episodes).
     Eval the champion on fresh draws of the harder world (it fails by strategy), run ONE coaching
     round (Opus rewrites the playbook from the champion's conduct), eval the new player on fresh
     held-out draws (it passes). Confirms live what the ship-gate proves model-free.

  python run_worldsmith.py                       # section 1 only (free, model-free ship-gate)
  python run_worldsmith.py --backend mock        # + plumbing of the closed loop (floor-player)
  python run_worldsmith.py --backend real        # + the LIVE closed-loop demonstration (~$1)
"""

import argparse
import os

from hta import llm
from hta.config import Config
from hta.ch2 import world_smith as ws
from hta.ch2 import worlds

_HERE = os.path.dirname(os.path.abspath(__file__))
CHAMPION_DIR = os.path.join(_HERE, "hta", "ch2", "champion")  # the recorded gen_0001 disposition


def print_gate(g: dict) -> None:
    flags = []
    for k in ("hard", "solvable", "ramp_ok", "room", "champion_fails"):
        flags.append(("" if g[k] else "!") + k.upper())
    print(f"  {g['name']:<14} floor {g['floor']:>4.1f}  heur {g['best_heur']:>5.2f}  oracle {g['oracle']:>5.2f}"
          f"  | gap {g['gap_norm']:.2f}n  heur {g['heur_norm']:.2f}n")
    print(f"  {'':<14} champion(commit-deepest) norm={g['champion_norm']:.2f} (raw {g['champion_raw']:.1f})"
          f"   fix(scout-then-commit) norm={g['fix_norm']:.2f} (raw {g['fix_raw']:.1f})")
    print(f"  {'':<14} {'  '.join(flags)}   ==>  {'SHIP' if g['ship'] else 'hold'}")


def main():
    ap = argparse.ArgumentParser(description="World-smith: structurally-harder world + closed-loop demo")
    ap.add_argument("--backend", choices=["mock", "real", "none"], default="none",
                    help="none = section-1 ship-gate only (free); mock = + plumbing; real = + LIVE demo")
    ap.add_argument("--n-eval", type=int, default=4, help="fresh draws per side of the closed loop")
    ap.add_argument("--champion", default=CHAMPION_DIR, help="champion node dir (has playbook.md)")
    ap.add_argument("--out-dir", default="outputs/worldsmith")
    ap.add_argument("--sandbox", choices=["none", "docker"], default=None)
    args = ap.parse_args()

    print("=" * 100)
    print("1. SHIP-GATE (model-free) — does the FORK re-open a gap the champion's method cannot close?")
    print("=" * 100)
    print("  The integrity wall, lifted: the inventor proposes only STRUCTURE; the oracle + coverage")
    print("  are re-derived mechanically; a world ships only if HARD + SOLVABLE + the champion FAILS")
    print("  (fail-now-but-learnable). Control first (no fork -> champion already wins -> hold):\n")
    control = ws.ship_gate(worlds.single_chain_spec())
    print_gate(control)
    print()
    harder = worlds.decoy_spec()
    gate = ws.ship_gate(harder)
    print_gate(gate)
    print(f"\n  reading: the SAME champion method reaches the oracle on the no-fork control "
          f"({control['champion_norm']:.2f}n) but collapses to the floor on the fork "
          f"({gate['champion_norm']:.2f}n); the new method (scout the gate, then commit) recovers it "
          f"({gate['fix_norm']:.2f}n). The fork — not difficulty — is what breaks 'commit to the deepest'.")
    if not gate["ship"]:
        print("\n  ship-gate did NOT pass — the harder world would not ship. Stopping.")
        return

    if args.backend == "none":
        print("\n  (section 1 only; pass --backend real to run the LIVE closed-loop demonstration)")
        return

    cfg = Config()
    cfg.backend = args.backend
    cfg.out_dir = args.out_dir
    cfg.eval_repeats = 1
    if args.sandbox:
        cfg.sandbox = args.sandbox
    llm.reset_accounting()

    print("\n" + "=" * 100)
    print(f"2. CLOSED LOOP ({'LIVE' if cfg.backend == 'real' else 'plumbing'}) — champion fails -> one "
          f"coaching round -> new player passes")
    print("=" * 100)
    if not os.path.exists(os.path.join(args.champion, "playbook.md")):
        print(f"  no champion playbook at {args.champion}; cannot run the closed loop.")
        return
    rep = ws.demonstrate(args.champion, harder, cfg, n_eval=args.n_eval)

    print("\n" + "=" * 100)
    print("RESULT")
    print("=" * 100)
    c0, c1 = rep["champion"]["mean_norm"], rep["coached"]["mean_norm"]
    print(f"  champion on the harder world : {c0:.2f}n  (solved {rep['champion']['solved']}/{rep['champion']['n_worlds']})")
    print(f"  coached  on held-out draws   : {c1:.2f}n  (solved {rep['coached']['solved']}/{rep['coached']['n_worlds']})")
    print(f"  closed the structural gap by : {rep['closed']:+.2f}n")
    acct = llm.accounting()
    print(f"\ncost: {acct['calls']} claude -p calls, ${acct['cost_usd']:.4f}  by_role={acct['by_role']}")


if __name__ == "__main__":
    main()
