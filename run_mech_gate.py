"""Mechanism-world FREE structural gate (no LLM, no cost).

Before spending a cent on live Haiku, confirm the new substrate has the right *shape* -- the
three properties the tape-world's separability could never give us together:

  gap        : a structure-reading player (realizable) beats the false-compass floor by a
               real margin -> there is room for taste to express.
  ramp       : fully inferring an f-fraction of the modules recovers ~f of the wiring
               (R^2 ~ 1) -> partial taste buys proportional coverage, a weak model can climb.
  deception  : treating what lights up as the wiring (the loud move) is substantially WRONG
               -> the false and true compasses diverge (high for deep chains, ~0 for stars).

These are necessary preconditions of the world, computed model-free. They do NOT prove a
weak model can realize the gap -- that is the live gate (next step), exactly as Chapter 2's
slice answered bet 2 structurally before measuring bet 1 live.

Usage:  python run_mech_gate.py
"""

from hta.mech import graph
from hta.mech.graph import MechSpec, Module

M = Module

SPECS = [
    # deep chains: long influence paths -> the loud root suggests it drives everything,
    # but it only directly drives the next link. Maximum deception.
    MechSpec("chains", (M("chain", 4), M("chain", 4), M("chain", 4)), budget=8),
    # stars: a hub directly drives its leaves -> what lights up IS the wiring. Near-zero
    # deception; the easy end of the family (a sanity contrast, not a taste test).
    MechSpec("stars", (M("star", 4), M("star", 4), M("star", 4)), budget=8),
    # balanced trees: medium depth -> some transitive confusion, some directness.
    MechSpec("trees", (M("tree", 7), M("tree", 7)), budget=8),
    # mixed: heterogeneous modules force allocation across different shapes.
    MechSpec("mixed", (M("chain", 5), M("star", 4), M("tree", 7)), budget=9),
    # deep+small: a dominant deep chain beside small modules (stepping-stone allocation).
    MechSpec("deep", (M("chain", 6), M("chain", 3), M("star", 3), M("tree", 4)), budget=9),
]


def run(specs):
    rows = []
    for spec in specs:
        ref = graph.references(spec)
        curve = graph.ramp_curve(spec)
        r2 = graph.linearity_r2(curve)
        _, edges, _, _ = graph.expand(spec)
        gap = ref["realizable_f1"] - ref["floor_f1"]
        shapes = "+".join(f"{m.kind}{m.size}" for m in spec.modules)
        print(f"\n== {spec.name} ==  N={spec.N} budget={spec.budget} edges={len(edges)}  [{shapes}]")
        print(f"  floor_f1={ref['floor_f1']:.3f}  realizable_f1={ref['realizable_f1']:.3f}  "
              f"oracle_f1={ref['oracle_f1']:.1f}  gap={gap:+.3f}")
        print(f"  deception(loud reading wrong)={ref['deception']:.3f}  "
              f"naive_precision={ref['naive_precision']:.3f}")
        print(f"  ramp curve={[round(c, 3) for c in curve]}  R^2={r2:.3f}")
        rows.append({"name": spec.name, "gap": gap, "r2": r2, "deception": ref["deception"],
                     "floor": ref["floor_f1"], "realizable": ref["realizable_f1"]})
    return rows


def gate(rows):
    n = len(rows)
    mean = lambda k: sum(r[k] for r in rows) / n
    g_gap, g_r2 = mean("gap"), mean("r2")
    # deception is intentionally shape-dependent (stars ~0); judge it on the worlds meant to
    # be deceptive (gap-bearing ones), reported as the max so a star can't mask a chain.
    max_dec = max(r["deception"] for r in rows)
    gap_ok = g_gap >= 0.10
    ramp_ok = g_r2 >= 0.95
    dec_ok = max_dec >= 0.30
    print("\n" + "=" * 64)
    print(f"AGGREGATE over {n} mechanisms:")
    print(f"  gap (realizable - floor):  mean={g_gap:+.3f}  -> {'PASS' if gap_ok else 'FAIL'}")
    print(f"  ramp (linear coverage):    mean R^2={g_r2:.3f} -> {'PASS' if ramp_ok else 'FAIL'}")
    print(f"  deception (max over maps): {max_dec:.3f}     -> {'PASS' if dec_ok else 'FAIL'}")
    ok = gap_ok and ramp_ok and dec_ok
    if ok:
        print("  VERDICT: shape is right (gap + ramp + deception). NEXT: live Haiku gate "
              "(does a weak model realize the gap?).")
    else:
        print("  VERDICT: shape is wrong; fix the world before any live spend.")
    print("=" * 64)
    return ok


if __name__ == "__main__":
    gate(run(SPECS))
