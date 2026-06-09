#!/usr/bin/env python3
"""The WORLD-SMITH — the second loop's first deliverable: the **closed-loop demonstration**
(ROADMAP.md -> "The two loops"; RESET_DESIGN.md -> the integrity wall lifted to the world-smith).

The first loop proved the player can be coached to a world's edge (seed -> gen_0001, held-out
0.50 -> 1.00). `run_probe.py` then showed no *scalar* crank of the anchor re-opens a gap — the
champion's "commit to the deepest chain" survives every dial. So the gradient lives in the world's
STRUCTURE. This builds the curriculum half that evolves that structure, and runs TWO iterations of
the two-loop (`world_smith.CURRICULUM`), each coached player carrying forward as the next champion:

  1. SHIP-GATE (model-free, free, deterministic). Each move authors a structurally harder world and
     the harness re-derives the oracle + coverage MECHANICALLY, shipping it only if it is HARD
     (oracle >> every generic planner), SOLVABLE (a reachable method reaches the oracle), and in the
     ZPD (the CHAMPION's method fails while the new method succeeds — fail-now-but-learnable):
       * iteration 1 — the DECOY fork (`worlds.decoy_spec`): two candidate chains + a GATE whose
         hidden value says which is live, so commit-to-the-deepest pins zero valley. Fix: scout THE
         gate, then commit.
       * iteration 2 — the gate LADDER (`worlds.ladder_spec`): the live chain is selected by an
         ADAPTIVE ladder of gates, so the decoy's own fix (scout THE gate) now reads only the first
         rung and fails. Fix: scout the ladder step by step, then commit.
     A no-fork control (above threshold, the champion still wins) shows it is STRUCTURE, not difficulty.

  2. CLOSED LOOP (live, `--backend real`, ~$1 per Opus coaching round + cents of Haiku episodes).
     For each move: eval the current champion on fresh draws (it fails by strategy), run ONE coaching
     round (Opus rewrites the playbook from its conduct), eval the new player on fresh held-out draws
     (it passes), and carry that graduate forward as the next move's champion — the outer loop closing.

  python run_worldsmith.py                       # section 1 only (free, model-free ship-gate)
  python run_worldsmith.py --backend mock        # + plumbing of the closed loop (floor-player)
  python run_worldsmith.py --backend real        # + the LIVE two-iteration closed loop (~$1/round)
"""

import argparse
import os

from hta import llm
from hta.config import Config
from hta.ch2 import world_smith as ws
from hta.ch2 import worlds

_HERE = os.path.dirname(os.path.abspath(__file__))
CHAMPION_DIR = os.path.join(_HERE, "hta", "ch2", "champion")  # the recorded gen_0001 disposition


def print_gate(g: dict, champ_label: str = "commit-deepest", fix_label: str = "scout-then-commit") -> None:
    flags = []
    for k in ("hard", "solvable", "ramp_ok", "room", "champion_fails"):
        flags.append(("" if g[k] else "!") + k.upper())
    print(f"  {g['name']:<14} floor {g['floor']:>4.1f}  heur {g['best_heur']:>5.2f}  oracle {g['oracle']:>5.2f}"
          f"  | gap {g['gap_norm']:.2f}n  heur {g['heur_norm']:.2f}n")
    print(f"  {'':<14} champion({champ_label}) norm={g['champion_norm']:.2f} (raw {g['champion_raw']:.1f})"
          f"   fix({fix_label}) norm={g['fix_norm']:.2f} (raw {g['fix_raw']:.1f})")
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
    print("1. SHIP-GATE (model-free) — does each structural MOVE re-open a gap its champion can't close?")
    print("=" * 100)
    print("  The integrity wall, lifted: the inventor proposes only STRUCTURE; the oracle + coverage")
    print("  are re-derived mechanically; a world ships only if HARD + SOLVABLE + the champion FAILS")
    print("  (fail-now-but-learnable). Control first (no fork -> champion already wins -> hold):\n")
    print_gate(ws.ship_gate(worlds.single_chain_spec()))
    print()
    gates = []
    for mv in ws.CURRICULUM:
        spec = mv["spec"]()
        g = ws.ship_gate(spec, champion_method=mv["champion"], fix_method=mv["fix"])
        print(f"  {mv['label']}")
        print_gate(g, champ_label=mv["champion"].__name__, fix_label=mv["fix"].__name__)
        print()
        gates.append((mv, g))
    print("  reading: each move's CHAMPION is the prior move's graduate — commit-to-the-deepest fails")
    print("  the decoy fork; its fix (scout the gate) then fails the gate LADDER, which only the")
    print("  adaptive scout closes. Each step breaks the last by STRUCTURE, not by a bigger number.")
    if not all(g["ship"] for _, g in gates):
        print("\n  a move did NOT pass the ship-gate — stopping (it would not ship).")
        return

    if args.backend == "none":
        print("\n  (section 1 only; pass --backend real to run the LIVE two-iteration closed loop)")
        return

    cfg = Config()
    cfg.backend = args.backend
    cfg.out_dir = args.out_dir
    cfg.eval_repeats = 1
    if args.sandbox:
        cfg.sandbox = args.sandbox
    llm.reset_accounting()

    print("\n" + "=" * 100)
    print(f"2. CLOSED LOOP ({'LIVE' if cfg.backend == 'real' else 'plumbing'}) — TWO iterations of the "
          f"two-loop; each coached player carries forward as the next champion")
    print("=" * 100)
    if not os.path.exists(os.path.join(args.champion, "playbook.md")):
        print(f"  no champion playbook at {args.champion}; cannot run the closed loop.")
        return
    results = ws.run_curriculum(args.champion, cfg, n_eval=args.n_eval)

    print("\n" + "=" * 100)
    print("RESULT — two iterations of the two-loop")
    print("=" * 100)
    for r in results:
        rep = r["rep"]
        if rep is None:
            print(f"  {r['label']}: did not ship; skipped.")
            continue
        c0, c1 = rep["champion"]["mean_norm"], rep["coached"]["mean_norm"]
        print(f"  {r['label']}")
        print(f"    champion on '{r['spec']}'   : {c0:.2f}n  (solved {rep['champion']['solved']}/{rep['champion']['n_worlds']})")
        print(f"    coached  on held-out draws : {c1:.2f}n  (solved {rep['coached']['solved']}/{rep['coached']['n_worlds']})")
        print(f"    closed the structural gap  : {rep['closed']:+.2f}n")
    acct = llm.accounting()
    print(f"\ncost: {acct['calls']} claude -p calls, ${acct['cost_usd']:.4f}  by_role={acct['by_role']}")


if __name__ == "__main__":
    main()
