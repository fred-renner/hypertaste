"""Chapter-2 thin de-risking slice — the measurement (WORLD_DESIGN.md -> "First slice").

Builds the hand-built grammar-maps, computes the model-free references (oracle / floor) and
the structural smoothness curve for free, then runs vanilla-vs-taste Haiku and reports the
two load-bearing bets plus a decision gate.

  bet 1 (realizable gap): taste-Haiku should beat vanilla-Haiku and approach the oracle.
  bet 2 (ramp not cliff):  coverage should be ~linear in the fraction of grammar inferred.

Usage:
  python run_slice.py --backend mock                 # free, deterministic plumbing check
  python run_slice.py --backend real --repeats 2     # live Haiku; a few cents/episode
"""

import argparse

from hta import llm
from hta.config import Config
from hta.ch2 import agent, grammar
from hta.ch2.maps import MAPS, by_name
from hta.ch2.world import TapeWorld


def _run_agent(spec, taste, cfg, repeats, log):
    world = TapeWorld(spec)
    raws, norms = [], []
    for _ in range(repeats):
        recon = agent.solve(spec, taste, cfg, log=log)
        sc = world.score(recon)
        raws.append(sc["raw"])
        norms.append(sc["normalized"])
    return sum(raws) / len(raws), sum(norms) / len(norms)


def run(cfg: Config, specs, repeats: int, log=print) -> dict:
    rows = []
    for spec in specs:
        world = TapeWorld(spec)
        ref = world.references()
        curve = grammar.smoothness_curve(spec)
        r2 = grammar.linearity_r2(curve)
        log(f"\n== {spec.name} ==  M={spec.M} K={spec.K} budget={spec.budget} "
            f"segments={[s.length for s in spec.segments]}")
        log(f"  references: floor_raw={ref['floor_raw']:.3f}  oracle_raw={ref['oracle_raw']:.3f}  "
            f"(determined: floor={ref['floor_det']} oracle={ref['oracle_det']}/{spec.M})")
        log(f"  smoothness curve (coverage vs #segments inferred): "
            f"{[round(c, 3) for c in curve]}  R^2={r2:.3f}")
        van_raw, van_norm = _run_agent(spec, False, cfg, repeats, log)
        tas_raw, tas_norm = _run_agent(spec, True, cfg, repeats, log)
        log(f"  vanilla: raw={van_raw:.3f} norm={van_norm:.3f}    "
            f"taste: raw={tas_raw:.3f} norm={tas_norm:.3f}    "
            f"gap(taste-vanilla)={tas_raw - van_raw:+.3f}")
        rows.append({"name": spec.name, "M": spec.M, "ref": ref, "r2": r2,
                     "van_raw": van_raw, "van_norm": van_norm,
                     "tas_raw": tas_raw, "tas_norm": tas_norm})
    return _gate(rows, log)


def _gate(rows, log) -> dict:
    n = len(rows)
    mean = lambda k: sum(r[k] for r in rows) / n
    g_van, g_tas = mean("van_raw"), mean("tas_raw")
    g_van_n, g_tas_n = mean("van_norm"), mean("tas_norm")
    g_r2 = mean("r2")
    gap = g_tas - g_van
    # bet 1: taste clears vanilla by a real margin AND lands meaningfully up the
    # floor->oracle ramp (normalized >= 0.5, and clearly above vanilla normalized).
    bet1 = "PASS" if (gap >= 0.10 and g_tas_n >= 0.50 and g_tas_n - g_van_n >= 0.15) else \
           ("INCONCLUSIVE" if gap >= 0.05 else "FAIL")
    bet2 = "PASS" if g_r2 >= 0.95 else ("INCONCLUSIVE" if g_r2 >= 0.85 else "FAIL")
    log("\n" + "=" * 64)
    log(f"AGGREGATE over {n} maps:")
    log(f"  vanilla raw={g_van:.3f} norm={g_van_n:.3f}   taste raw={g_tas:.3f} norm={g_tas_n:.3f}")
    log(f"  bet 1 (realizable gap):  taste-vanilla={gap:+.3f}, taste_norm={g_tas_n:.3f} -> {bet1}")
    log(f"  bet 2 (ramp not cliff):  mean R^2={g_r2:.3f} -> {bet2}")
    if bet1 == "PASS" and bet2 == "PASS":
        verdict = "BUILD THE LOOP: both bets clear; the taste gap is Haiku-realizable on a ramp."
    elif bet2 != "PASS":
        verdict = "FIX THE GRAMMAR: inference is not a ramp; make productions more composable."
    else:
        verdict = "ITERATE on difficulty/prompt before the loop: gap not yet realizable by Haiku."
    log(f"  DECISION: {verdict}")
    log("=" * 64)
    return {"rows": rows, "bet1": bet1, "bet2": bet2, "gap": gap,
            "taste_norm": g_tas_n, "r2": g_r2, "verdict": verdict}


def main():
    ap = argparse.ArgumentParser(description="Chapter-2 thin de-risking slice measurement")
    ap.add_argument("--backend", choices=["mock", "real"], default="mock")
    ap.add_argument("--repeats", type=int, default=1, help="episodes per (map, agent); real runs raise this to damp Haiku variance")
    ap.add_argument("--map", dest="map_name", default=None, help="run a single map by name")
    ap.add_argument("--task-model", default=None)
    args = ap.parse_args()

    cfg = Config()
    cfg.backend = args.backend
    if args.task_model:
        cfg.task_model = args.task_model
    specs = [by_name(args.map_name)] if args.map_name else MAPS
    llm.reset_accounting()
    run(cfg, specs, max(1, args.repeats))
    acct = llm.accounting()
    print(f"\ncost: {acct['calls']} claude -p calls, ${acct['cost_usd']:.4f}  by_role={acct['by_role']}")


if __name__ == "__main__":
    main()
