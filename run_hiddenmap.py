#!/usr/bin/env python3
"""Build-screen the Pass-3 **hidden-map family** (PLAN.md -> "The staged passes" 3a). Model-free,
pure compute, no LLM tokens — the same gate discipline as `run_anchor.py`, lifted to the world
where the *topology* is hidden:

  1. VALIDATE the screen: below-threshold controls (no coupling/depth so the myopic gradient is
     optimal; a slack budget so allocation is trivial) must read gap ~ 0; the canonical world
     must read a real gap best-play reaches but no generic planner (greedy/2-step lookahead) can.
  2. SWEEP the dials (deep-region mass, budget, structure) and tabulate every gate:
     no-free-coverage (the plodder's old job, now a screen gate), hard/solver-proof, solvable
     (the articulable reference method attains the band ceiling), anti-cliff, room.
  3. RECOMMEND the cheapest spec clearing every gate; `hidden_map.canonical_spec()` is the pick.

Plus the Pass-3b smoke path (the only part that can spend money):

  python run_hiddenmap.py                       # the free build gate (1-3)
  python run_hiddenmap.py --smoke               # + one mock episode, trajectory rendered
  python run_hiddenmap.py --smoke --backend real  # + one LIVE Haiku episode (cents)
"""

import argparse
import time

from hta.ch2 import hidden_map as hm
from hta.ch2.hidden_map import GroupSpec, HiddenMapSpec


def fmt_row(s):
    if not s.get("valid"):
        return f"{s['name']:<16} INVALID: {'; '.join(s['issues'])}"
    flags = [g for g in ("no_free_coverage", "hard", "solvable", "anti_cliff", "room")
             if s[g]]
    return (f"{s['name']:<16} H={s['n_hyps']:>4} P={s['n_probe_cols']:>2} B={s['budget']} "
            f"| oracle {s['oracle']:>5.2f} heur {s['best_heur']:>5.2f} method {s['method']:>5.2f} "
            f"| gap {s['gap_norm']:>4.2f}n heur_n {s['heur_norm']:>4.2f} cliff {s['cliff']:>4.2f} "
            f"| {' '.join(flags)}{'  => SHIP' if s['ship'] else ''}")


def candidates():
    """The dial sweep around the canonical: deep-region mass, budget, and structure. Every row is
    screened on all five gates; the canonical is the cheapest that clears them all."""
    deep = GroupSpec(layers=(2, 2, 2), region_len=8, coupled=True)
    mid = GroupSpec(layers=(2,), region_len=5, coupled=True)
    bait = GroupSpec(layers=(), region_len=2, coupled=False)
    return [
        HiddenMapSpec("hm-shallowdeep", groups=(GroupSpec(layers=(2, 2), region_len=8,
                                                          coupled=True), mid, bait, bait), budget=6),
        HiddenMapSpec("hm-smalldeep", groups=(GroupSpec(layers=(2, 2, 2), region_len=5,
                                                        coupled=True), mid, bait, bait), budget=6),
        hm.canonical_spec(),
        HiddenMapSpec("hm-bigdeep", groups=(GroupSpec(layers=(2, 2, 2), region_len=11,
                                                      coupled=True), mid, bait, bait), budget=6),
        HiddenMapSpec("hm-tight", groups=(deep, mid, bait, bait), budget=5),
        HiddenMapSpec("hm-roomy", groups=(deep, mid, bait, bait), budget=7),
        HiddenMapSpec("hm-nomid", groups=(deep, bait, bait), budget=6),
        HiddenMapSpec("hm-twodeep", groups=(deep, GroupSpec(layers=(2, 2), region_len=6,
                                                            coupled=True), bait, bait), budget=7),
    ]


def main():
    ap = argparse.ArgumentParser(description="Build-screen the hidden-map family (Pass 3)")
    ap.add_argument("--smoke", action="store_true",
                    help="skip the gate; run one episode on the canonical world instead")
    ap.add_argument("--backend", choices=["mock", "real"], default="mock")
    args = ap.parse_args()

    if args.smoke:
        print(f"SMOKE — one {args.backend} episode on the canonical world, trajectory rendered")
        smoke(args.backend)
        return

    print("=" * 110)
    print("1. SCREEN VALIDATION — do the controls read below threshold while the canonical reads a real gap?")
    print("=" * 110)
    bait = GroupSpec(layers=(), region_len=2, coupled=False)
    ctrl_flat = HiddenMapSpec("ctrl-flat", groups=(bait,) * 4, budget=4)   # no depth, no coupling
    ctrl_slack = HiddenMapSpec("ctrl-slack", groups=hm.canonical_spec().groups, budget=12)
    treat = hm.canonical_spec()
    rows = [hm.screen(s) for s in (ctrl_flat, ctrl_slack, treat)]
    for s in rows:
        verdict = "ABOVE" if s.get("hard") else "below"
        print(f"  {fmt_row(s)}  -> {verdict}")
        print("      planners: " + "  ".join(f"{k}={v:.2f}" for k, v in s["heurs"].items()))
    ok = (not rows[0]["hard"]) and (not rows[1]["hard"]) and rows[2]["hard"]
    print(f"\n  screen separates the controls from the treatment: {ok}")

    print("\n" + "=" * 110)
    print("2. DIAL SWEEP — every gate, every row (no-free-coverage / hard / solvable / anti-cliff / room)")
    print("=" * 110)
    t0 = time.time()
    swept = [hm.screen(s) for s in candidates()]
    for s in swept:
        print(f"  {fmt_row(s)}")
    print(f"  ({time.time() - t0:.0f}s, model-free)")

    print("\n" + "=" * 110)
    print("3. RECOMMENDATION — cheapest spec clearing ALL gates")
    print("=" * 110)
    ship = [s for s in swept if s.get("ship")]
    if not ship:
        print("  No spec clears every gate — re-dial the deep-region mass or the budget.")
        return
    # Most central planner band first (the model-free proxy for landing a live student in-band,
    # with margin both ways — every family here is cheap to score, so compute is not the
    # tiebreak the way it was for run_anchor); then the smaller family.
    mid_band = (hm.HEUR_LO + hm.HEUR_HI) / 2
    ship.sort(key=lambda s: (abs(s["heur_norm"] - mid_band), s["n_hyps"], s["budget"]))
    pick = ship[0]
    canon = hm.screen(hm.canonical_spec())
    print(f"  -> {pick['name']}   (canonical_spec() is {canon['name']}: ship={canon['ship']})")
    print(f"     {fmt_row(pick)}")
    print(f"     best-play {pick['oracle']:.2f} vs best generic planner {pick['best_heur']:.2f} "
          f"({pick['gap_norm']:.0%} of the 0->best-play band; floor is 0 by construction)")
    print(f"     the articulable reference method reaches {pick['method_norm']:.0%} of the band "
          f"(solvable), planners land at {pick['heur_norm']:.0%} (live-student room)")


def smoke(backend: str):
    from hta import llm
    from hta.config import Config
    from hta.ch2 import loop as ch2_loop, trajectory
    from hta.ch2.episode_state import draw_hstar

    cfg = Config()
    cfg.backend = backend
    spec = hm.canonical_spec()
    hstar = draw_hstar(spec, seed=42)
    with open(f"{ch2_loop.SEED_DIR}/playbook.md") as f:
        playbook = f.read()
    llm.reset_accounting()
    rec = ch2_loop.run_episode(playbook, spec, hstar, cfg)
    print(trajectory.render(spec, rec["result"], score=rec["score"]))
    if backend == "real":
        acct = llm.accounting()
        print(f"\ncost: {acct['calls']} claude -p calls, ${acct['cost_usd']:.4f}")


if __name__ == "__main__":
    main()
