#!/usr/bin/env python3
"""Build-screen the Chapter-2 **anchor family** — the B2-allocation trail world
(RESET_DESIGN.md -> "The world design" / "Next actions: Anchor family"). Model-free, pure
compute, no LLM tokens. The same gate as `run_threshold.py`, lifted from the register world
(where *inference* is hard, B1) to a world where inference is a trivial lookup but *allocation*
is hard (B2):

  1. VALIDATE the screen: a below-threshold control (no deep payoff, or a slack budget so
     allocation is trivial) must read gap ~ 0; the trail must read a real gap the belief-MDP
     oracle reaches but no greedy/2-step-lookahead policy can.
  2. SWEEP the gap dial (the lode-to-lure mass ratio `Lv`, the budget, the probe cost) and
     tabulate: threshold gap, ramp anti-cliff, and where the best heuristic lands in the
     floor->oracle band (the Haiku-reachable room).
  3. RECOMMEND the cheapest spec that clears the gate (gap_norm >= MARGIN) while keeping the
     ramp anti-cliff and leaving Haiku room (heur_norm in the realizable middle band).

The gap lives in a **chain-gated payoff under deception**. A *trail* of signpost registers
(root -> relay -> lode) gates a big vault; reading a signpost pays ZERO coverage (it is an
instrument, not a map cell) and the vault is inference-only (reconstructed, never drilled). So no
prefix of the chain pays — a bounded planner cannot climb it — and because there are at least as
many fat *lure* blocks as the budget, spending a probe on a zero-coverage signpost has a strict
opportunity cost. The greedy/2-step planner takes the lures; only the full oracle commits the
three probes to the lode. Reconstruction stays a lookup throughout (B2), so the gap survives an
English playbook (you cannot brute-force a chain search in prose) and the lode's identity is
hidden in the seed, learnable only by playing this instance.

Run: python run_anchor.py
"""

from hta.ch2.anchor import TrailSpec, screen

MARGIN = 0.15      # gap_norm a world must clear to be "above threshold" (tacit room to matter)
CLIFF = 0.55       # max single-step ramp jump (bet 2, anti-cliff). The chain payoff is convex, so
                   # R^2 < 1 is intrinsic; the honest check is that no step is all-or-nothing.
HEUR_LO, HEUR_HI = 0.15, 0.80  # best-heuristic band: room above floor, below oracle


def ramp_ok(s):
    return s["ramp_monotone"] and s["ramp_maxstep"] <= CLIFF


def candidates():
    """A curated ladder over the trail family: controls (below threshold), the gap dial `Lv`, the
    cost knob, and the canonical anchor. `relays`/`lodes` are the public pointer tree; the hidden
    seed (register values) fixes where the realized trail ends."""
    base = dict(R=10, K=2, Ld=2, Lv=9, root=0, relays=(1, 2), lodes=((3, 4), (5, 6)), budget=3)
    return [
        # --- controls: no deep payoff / slack budget -> allocation is trivial -> below ---
        TrailSpec("ctrl-novault", **{**base, "Lv": 0}),
        TrailSpec("ctrl-slack",   **{**base, "budget": 6}),      # lures < budget -> chain climbable
        # --- the gap dial: the lode-to-lure mass ratio Lv (more lode -> bigger gap, steeper ramp) ---
        TrailSpec("trail-Lv5",    **{**base, "Lv": 5}),
        TrailSpec("trail-Lv7",    **{**base, "Lv": 7}),
        TrailSpec("trail-anchor", **base),                       # Lv=9: mid-band, the recommended pick
        TrailSpec("trail-Lv12",   **{**base, "Lv": 12}),
        # --- the variable-cost virtue: a costlier lure sharpens the cost-weighted gap ---
        TrailSpec("trail-cost",   **{**base, "cost_lure": 2, "budget": 4}),
    ]


def fmt_row(s):
    return (f"{s['name']:<14} H={s['n_hyps']:>4} B={s['budget']} Lv={s['Lv']:>2} "
            f"| floor {s['floor']:>4.1f} heur {s['best_heur']:>5.2f} oracle {s['oracle']:>5.2f} "
            f"| gap {s['gap_raw']:>4.2f} ({s['gap_norm']:>5.2f}n) "
            f"heur_n {s['heur_norm']:>5.2f} maxstep {s['ramp_maxstep']:>4.2f}")


def main():
    print("=" * 104)
    print("1. SCREEN VALIDATION — does the gate separate a below-threshold control from the trail?")
    print("=" * 104)
    base = dict(R=10, K=2, Ld=2, Lv=9, root=0, relays=(1, 2), lodes=((3, 4), (5, 6)), budget=3)
    ctrl = screen(TrailSpec("ctrl-novault", **{**base, "Lv": 0}))
    treat = screen(TrailSpec("trail-anchor", **base))
    for s in (ctrl, treat):
        verdict = "ABOVE" if s["gap_norm"] >= MARGIN else "below"
        print(f"  {fmt_row(s)}  -> {verdict}")
        print("      heuristics: " + "  ".join(f"{k}={v:.2f}" for k, v in s["heurs"].items())
              + f"   clairvoyant={s['clairvoyant']:.2f}")
    ok = ctrl["gap_norm"] < MARGIN <= treat["gap_norm"]
    print(f"\n  screen separates control from treatment: {ok}")
    print(f"  clairvoyant == oracle on the anchor ({treat['clairvoyant']:.2f}=={treat['oracle']:.2f}): "
          f"{abs(treat['clairvoyant'] - treat['oracle']) < 1e-9}  "
          f"-> the gap is the price of the optimal POLICY's form, not of not knowing the world")

    print("\n" + "=" * 104)
    print("2. DIFFICULTY SWEEP — gap (threshold) vs ramp (anti-cliff) vs heur_norm (Haiku room)")
    print("=" * 104)
    rows = [screen(s, clair=False) for s in candidates()]
    for s in rows:
        flags = []
        if s["gap_norm"] >= MARGIN:
            flags.append("THRESH")
        if ramp_ok(s):
            flags.append("RAMP")
        if HEUR_LO <= s["heur_norm"] <= HEUR_HI:
            flags.append("ROOM")
        print(f"  {fmt_row(s)}  {' '.join(flags)}")

    print("\n" + "=" * 104)
    print("3. RECOMMENDATION — cheapest spec clearing ALL three (THRESH + RAMP + ROOM)")
    print("=" * 104)
    band = [s for s in rows
            if s["gap_norm"] >= MARGIN and ramp_ok(s) and HEUR_LO <= s["heur_norm"] <= HEUR_HI]
    if not band:
        print("  No spec clears all three — widen the lode-to-lure ratio or tighten the budget.")
        return
    # cheapest first; then the most *central* heuristic (most realizable room for a live student,
    # neither flooring nor maxing — the model-free proxy for landing Haiku in-band, not a max-gap)
    mid = (HEUR_LO + HEUR_HI) / 2
    band.sort(key=lambda s: (s["n_hyps"], s["budget"], abs(s["heur_norm"] - mid)))
    pick = band[0]
    print(f"  -> {pick['name']}")
    print(f"     {fmt_row(pick)}")
    print(f"     threshold gap : oracle {pick['oracle']:.2f} vs best heuristic {pick['best_heur']:.2f}"
          f"  (+{pick['gap_raw']:.2f} raw, {pick['gap_norm']:.0%} of band)")
    print(f"     basket        : " + "  ".join(f"{k}={v:.2f}" for k, v in pick["heurs"].items())
          + "  -> none reaches the oracle = the optimal allocation is not a shallow rule")
    print(f"     Haiku room    : best heuristic at {pick['heur_norm']:.0%} of the floor->oracle band")
    print(f"     belief space  : {pick['n_hyps']} hypotheses, budget {pick['budget']} "
          f"— exact oracle by simulation, zero tokens; reconstruction is a lookup (B2)")
    print("\n  NOTE: this is the model-free pick. Like trap-tetra, it is NECESSARY not sufficient —")
    print("  follow it with a live calibration so Haiku lands in-band (RESET_DESIGN.md -> 'Wire +")
    print("  calibrate'). The binding axis here is allocation/search depth, not inference depth.")


if __name__ == "__main__":
    main()
