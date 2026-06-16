#!/usr/bin/env python3
"""PROBE (stage 1): does evolving the world by a SCALAR knob re-open a gap the champion fails to close?

We validated the agent loop (gen_0000 -> gen_0001: held-out 0.50 -> 1.00). We have NOT shown the
world can evolve to demand a *new* strategy. Stage 1 asks the cheap question first: take the
model-free HARDEST gated anchor variant (`trail-cost`: clearings cost 2, budget 4 -> lowest
heuristic room, heur_norm ~0.29) and live-eval the current champion playbook on fresh draws of it,
with the canonical world as a control.

The screen already shows every gated scalar variant keeps the SAME optimal policy (walk the trail);
only the stakes move. So the prediction is: the champion HOLDS on the scalar-harder world. If it
does, no scalar crank dislodges its policy -> a genuine "champion fails" world needs STRUCTURAL
evolution (a deeper/branching/adaptive trail), which is the world-smith's job (the second loop).

  python run_probe.py --backend real            # live (cents: a few Haiku episodes)
  python run_probe.py --backend mock            # offline plumbing (deterministic floor-player)
"""

import argparse

from hta import llm
from hta.config import Config
from hta._trail import anchor, loop
from hta._trail.episode_state import canonical_spec, draw_hstar

CHAMPION = "outputs/ch2b/archive/gen_0001"   # the playbook the agent loop just produced


def harder_spec() -> anchor.TrailSpec:
    """The model-free hardest GATED scalar variant (run_anchor.py sweep): variable cost shifts the
    cells-per-probe arithmetic the champion's allocation rule leans on -> the strongest scalar stress."""
    base = dict(R=10, K=2, Ld=2, Lv=9, trailhead=0, waypoints=(1, 2), landmarks=((3, 4), (5, 6)))
    return anchor.TrailSpec("trail-cost", **base, budget=4, cost_clearing=2)


def screen_line(spec: anchor.TrailSpec) -> None:
    s = anchor.screen(spec, clair=False)
    verdict = "ABOVE (gated)" if s["gap_norm"] >= 0.15 else "below"
    print(f"  {spec.name:<13} floor {s['floor']:>4.1f}  best-heur {s['best_heur']:>5.2f}  "
          f"oracle {s['oracle']:>5.2f}  | gap {s['gap_raw']:>4.2f} ({s['gap_norm']:.2f}n)  "
          f"heur_room {s['heur_norm']:.2f}  -> {verdict}")


def eval_champion(spec: anchor.TrailSpec, n: int, seed0: int, cfg: Config) -> dict:
    worlds = [(spec, draw_hstar(spec, seed0 + i)) for i in range(n)]
    rep = loop.evaluate(CHAMPION, worlds, cfg, log=lambda *a, **k: print("   ", *a))
    print(f"  => mean_norm={rep['mean_norm']:.2f}  solved(>=0.85)={rep['solved']}/{rep['n_worlds']}")
    return rep


def main():
    ap = argparse.ArgumentParser(description="Stage-1 scalar-harder probe of the champion playbook")
    ap.add_argument("--backend", choices=["mock", "real"], default="real")
    ap.add_argument("--n-harder", type=int, default=4, help="fresh draws of the harder world")
    ap.add_argument("--n-control", type=int, default=2, help="fresh draws of the canonical world")
    args = ap.parse_args()

    cfg = Config()
    cfg.backend = args.backend
    cfg.eval_repeats = 1
    llm.reset_accounting()

    spec_h, spec_c = harder_spec(), canonical_spec()
    print(f"== PROBE: scalar-harder world vs champion ({CHAMPION}) ==  backend={cfg.backend}")
    print("\n[re-screen the integrity gate — both must stay oracle >> heuristic]")
    screen_line(spec_c)
    screen_line(spec_h)

    print(f"\n[champion on HARDER world '{spec_h.name}' — {args.n_harder} fresh held-out draws]")
    eval_champion(spec_h, args.n_harder, 770_000, cfg)

    print(f"\n[champion on CONTROL world '{spec_c.name}' — {args.n_control} fresh held-out draws]")
    eval_champion(spec_c, args.n_control, 880_000, cfg)

    acct = llm.accounting()
    print(f"\ncost: {acct['calls']} claude -p calls, ${acct['cost_usd']:.4f}  by_role={acct['by_role']}")


if __name__ == "__main__":
    main()
