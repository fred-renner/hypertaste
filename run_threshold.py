#!/usr/bin/env python3
"""Find the right Chapter-2 world difficulty by the threshold gate (ROADMAP -> "earning its
keep"). Model-free, pure compute, no LLM tokens.

  1. VALIDATE the screen: an independent register world (the tape's structure) must read
     BELOW threshold (best articulable heuristic ~ the belief-MDP oracle); a coupled
     stepping-stone world must read ABOVE (a real gap the oracle reaches but no closed-form
     heuristic can).
  2. SWEEP a ladder of coupled topologies and tabulate: threshold gap, ramp R^2, and where
     a decent heuristic lands in the floor->oracle band (the Haiku-reachable room).
  3. RECOMMEND the starting world — the cheapest spec that clears the gate (gap_norm >=
     MARGIN) while keeping the ramp (R^2 >= RAMP_MIN) and leaving Haiku room (heur_norm in
     the realizable middle band).

The gap lives in *asymmetric* coupling. A linked block on two **hidden** registers (no direct
block) is self-determinable only by committing TWO local probes (solve the affine 2x2) — the
first probe pays zero determined cells. A myopic heuristic that ranks the next probe by
immediate determined-gain (or even by information) is lured to a paying anchor and never takes
the boring door; the belief-MDP oracle plans the two-probe commitment. That is the design's
"high-value region behind a boring door, beelining fails", made structural and measurable.

Run: python run_threshold.py
"""

from hta.ch2.threshold import LinkSpec, screen

MARGIN = 0.15      # gap_norm a world must clear to be "above threshold" (tacit room to matter)
CLIFF = 0.55       # max single-step ramp jump (bet 2, anti-cliff). NOT R^2=1.0: a coupled
                   # world is supermodular, so R^2<1 is intrinsic; the honest check is that no
                   # step is all-or-nothing (partial inference buys nothing then everything).
HEUR_LO, HEUR_HI = 0.15, 0.80  # best-heuristic band: room above floor, below oracle


def ramp_ok(s):
    return s["ramp_monotone"] and s["ramp_maxstep"] <= CLIFF


def candidates():
    """Curated worlds: a control, symmetric coupling (still articulable), and stepping-stone
    traps of growing size. `direct` naming a subset makes the rest hidden = behind a door."""
    K = 3
    return [
        # --- control: independent, all-direct (the tape's structure) -> below threshold ---
        LinkSpec("ctrl-indep",  R=3, K=K, Ld=2, Ll=2, edges=(), budget=2, direct=(0, 1, 2)),
        # --- symmetric coupling, all registers direct -> still greedy-solvable (contrast) ---
        LinkSpec("cyc3-direct", R=3, K=K, Ld=2, Ll=2,
                 edges=((0, 1), (1, 2), (0, 2)), budget=2, direct=(0, 1, 2)),
        # --- one buried pair behind a lure anchor (the minimal stepping stone) ---
        LinkSpec("trap-pair",   R=3, K=K, Ld=2, Ll=3, edges=((1, 2),), budget=2, direct=(0,)),
        LinkSpec("trap-pair-b3", R=3, K=K, Ld=2, Ll=3, edges=((1, 2),), budget=3, direct=(0,)),
        # --- lure anchor + a buried triangle (3 hidden regs, dense downstream) ---
        LinkSpec("trap-tri",    R=4, K=K, Ld=2, Ll=2,
                 edges=((1, 2), (1, 3), (2, 3)), budget=3, direct=(0,)),
        LinkSpec("trap-tri-b4", R=4, K=K, Ld=2, Ll=2,
                 edges=((1, 2), (1, 3), (2, 3)), budget=4, direct=(0,)),
        # --- two lure anchors + a buried pair: allocation among doors joins the trap ---
        LinkSpec("trap-2lure",  R=4, K=K, Ld=2, Ll=3,
                 edges=((2, 3),), budget=3, direct=(0, 1)),
        # --- deeper chain: a hidden register two hops from any anchor ---
        LinkSpec("trap-chain",  R=4, K=K, Ld=2, Ll=2,
                 edges=((0, 1), (1, 2), (2, 3)), budget=3, direct=(0,)),
        # --- bigger buried cluster, more headroom for the ramp ---
        LinkSpec("trap-quad",   R=5, K=K, Ld=2, Ll=2,
                 edges=((1, 2), (1, 3), (2, 3), (3, 4)), budget=4, direct=(0,)),
        # --- anchor-padded: extra direct registers add LINEAR ramp mass to flatten the low
        #     end (anti-cliff) while a buried triangle keeps the gap. The direct/linked mass
        #     ratio is the calibration dial that trades ramp curvature against the gap. ---
        LinkSpec("tri-2anchor", R=5, K=K, Ld=2, Ll=2,
                 edges=((2, 3), (2, 4), (3, 4)), budget=4, direct=(0, 1)),
        LinkSpec("tri-2anchor-b3", R=5, K=K, Ld=2, Ll=2,
                 edges=((2, 3), (2, 4), (3, 4)), budget=3, direct=(0, 1)),
        LinkSpec("pair-2anchor", R=4, K=K, Ld=2, Ll=3,
                 edges=((2, 3),), budget=3, direct=(0, 1)),
    ]


def fmt_row(s):
    return (f"{s['name']:<15} M={s['M']:>2} H={s['n_hyps']:>3} E={s['edges']:>1} B={s['budget']} "
            f"| floor {s['floor']:>4.1f} heur {s['best_heur']:>5.2f} "
            f"oracle {s['oracle']:>5.2f} clair {s['clairvoyant']:>5.2f} "
            f"| gap {s['gap_raw']:>4.2f} ({s['gap_norm']:>5.2f}n) "
            f"heur_n {s['heur_norm']:>5.2f} R2 {s['ramp_r2']:>4.2f}")


def main():
    print("=" * 104)
    print("1. SCREEN VALIDATION  — does the gate separate independent (below) from stepping-stone (above)?")
    print("=" * 104)
    ctrl = screen(LinkSpec("control", R=3, K=3, Ld=2, Ll=2, edges=(), budget=2, direct=(0, 1, 2)))
    treat = screen(LinkSpec("stepstone", R=4, K=3, Ld=2, Ll=2,
                            edges=((1, 2), (1, 3), (2, 3)), budget=3, direct=(0,)))
    for s in (ctrl, treat):
        verdict = "ABOVE" if s["gap_norm"] >= MARGIN else "below"
        print(f"  {fmt_row(s)}  -> {verdict}")
        print("      heuristics: " + "  ".join(f"{k}={v:.2f}" for k, v in s["heurs"].items()))
    ok = ctrl["gap_norm"] < MARGIN <= treat["gap_norm"]
    print(f"\n  screen separates control from treatment: {ok}")

    print("\n" + "=" * 104)
    print("2. DIFFICULTY SWEEP  — gap (threshold) vs ramp (bet 2) vs heur_norm (Haiku room)")
    print("=" * 104)
    rows = [screen(s) for s in candidates()]
    for s in rows:
        flags = []
        if s["gap_norm"] >= MARGIN:
            flags.append("THRESH")
        if ramp_ok(s):
            flags.append("RAMP")
        if HEUR_LO <= s["heur_norm"] <= HEUR_HI:
            flags.append("ROOM")
        print(f"  {fmt_row(s)}  maxstep {s['ramp_maxstep']:.2f}  {' '.join(flags)}")

    print("\n" + "=" * 104)
    print("3. RECOMMENDATION  — cheapest spec clearing ALL three (THRESH + RAMP + ROOM)")
    print("=" * 104)
    band = [s for s in rows
            if s["gap_norm"] >= MARGIN and ramp_ok(s)
            and HEUR_LO <= s["heur_norm"] <= HEUR_HI]
    if not band:
        # fall back to the strongest threshold-clearer so the report is still actionable
        thresh = [s for s in rows if s["gap_norm"] >= MARGIN]
        if not thresh:
            print("  No spec clears the threshold on this ladder — widen the coupling dial.")
            return
        print("  No spec clears all three; reporting the strongest threshold-clearer instead.")
        print("  (Tension: deeper traps lift the gap but bend the ramp / sink heur_norm.)")
        band = sorted(thresh, key=lambda s: -s["gap_norm"])[:1]
    else:
        band.sort(key=lambda s: (s["n_hyps"], s["M"], s["budget"]))  # cheapest first
    pick = band[0]
    print(f"  -> {pick['name']}")
    print(f"     {fmt_row(pick)}")
    print(f"     threshold gap : oracle {pick['oracle']:.2f} vs best heuristic "
          f"{pick['best_heur']:.2f}  (+{pick['gap_raw']:.2f} raw, {pick['gap_norm']:.0%} of band)")
    print(f"     basket        : " + "  ".join(f"{k}={v:.2f}" for k, v in pick["heurs"].items())
          + "  -> none reaches the oracle = the optimal policy is not closed-form")
    print(f"     ramp R^2      : {pick['ramp_r2']:.3f}")
    print(f"     Haiku room    : best heuristic at {pick['heur_norm']:.0%} of the floor->oracle band")
    print(f"     belief space  : {pick['n_hyps']} hypotheses, {pick['M']} cells, budget "
          f"{pick['budget']} — exact oracle instant, zero tokens")
    print("\n  Next: confirm live Haiku lands inside this band (above floor, below oracle) with")
    print("  headroom — the one measurement that needs the model, kept to its own session.")


if __name__ == "__main__":
    main()
