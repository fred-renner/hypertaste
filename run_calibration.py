"""Chapter-2 calibration — the one measurement that needs the model (CLAUDE.md -> "Next
action"). The threshold gate settled the world's difficulty model-free; this confirms the
**live student** lands inside the chosen world's floor->oracle band with headroom.

  above the no-inference floor  => Haiku is actually inferring, not just reading probes.
  below the belief-MDP oracle   => the loop has room to climb (the ZPD; the gap to grow into).

Difficulty calibrates to the live student, never a proxy (Chapter 1's paid lesson). If Haiku
floors, dial down (e.g. --spec tri-2anchor / tri-2anchor-b3, more anchor mass); if it maxes,
dial up. Each episode draws a fresh random register seed (sampling the prior the references
average over) and runs one single-session claude -p episode.

Usage:
  python run_calibration.py --backend mock                      # free, deterministic plumbing
  python run_calibration.py --backend real --episodes 8         # live Haiku; a few cents each
  python run_calibration.py --backend real --spec tri-2anchor   # a dial-down fallback world
"""

import argparse
import random

from hta import llm
from hta.config import Config
from hta.ch2 import register_world as rw
from hta.ch2.threshold import LinkSpec
from run_threshold import candidates

LO, HI = 0.15, 0.85  # in-band-with-headroom: clearly above floor, clearly below oracle


def _spec(name: str) -> LinkSpec:
    for s in candidates():
        if s.name == name:
            return s
    raise SystemExit(f"unknown spec {name!r}; choices: {[s.name for s in candidates()]}")


def _episode(spec, i, base_seed, cfg, log):
    """One episode on a fresh random world; returns (raw, valid, correct)."""
    rng = random.Random(base_seed + i)
    _, cells = rw.realize(spec, rng)
    recon = rw.solve(spec, cells, cfg, log=log)
    ref = rw.references(spec)
    s = rw.score(cells, recon, ref)
    log(f"  ep {i:>2}: raw={s['raw']:.3f} norm={rw.normalize(s['raw'], ref):.2f} "
        f"correct={s['correct']}/{s['M']} valid={s['valid']}")
    return s["raw"], s["valid"]


def run(cfg: Config, spec: LinkSpec, episodes: int, base_seed: int, log=print) -> dict:
    ref = rw.references(spec)
    band = ref["oracle_raw"] - ref["floor_raw"]
    log(f"== calibrate {spec.name} ==  M={spec.M} K={spec.K} budget={spec.budget} "
        f"hyps={spec.K ** spec.R}")
    log(f"  band (raw coverage): floor={ref['floor_raw']:.3f}  "
        f"best_heuristic={ref['best_heur_raw']:.3f} ({(ref['best_heur_raw']-ref['floor_raw'])/band:.0%})  "
        f"oracle={ref['oracle_raw']:.3f}   (determined: floor={ref['floor_det']:.0f} "
        f"heur={ref['best_heur_det']:.0f} oracle={ref['oracle_det']:.0f}/{spec.M})")
    log(f"  running {episodes} live episode(s)...")

    raws, valids = [], 0
    concurrency = max(getattr(cfg, "eval_concurrency", 1) or 1, 1)
    if cfg.backend == "mock" or concurrency <= 1 or episodes <= 1:
        results = [_episode(spec, i, base_seed, cfg, log) for i in range(episodes)]
    else:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(concurrency, episodes)) as ex:
            results = list(ex.map(lambda i: _episode(spec, i, base_seed, cfg, log),
                                  range(episodes)))
    for raw, valid in results:
        raws.append(raw)
        valids += int(valid)

    # Average raw, normalize ONCE (run_slice's lesson: averaging per-episode normalized scores
    # double-counts the [0,1] clamp).
    mean_raw = sum(raws) / len(raws)
    mean_norm = rw.normalize(mean_raw, ref)
    return _verdict(spec, ref, mean_raw, mean_norm, valids, episodes, log)


def _verdict(spec, ref, mean_raw, mean_norm, valids, episodes, log) -> dict:
    log("\n" + "=" * 72)
    log(f"AGGREGATE over {episodes} episode(s) on {spec.name}:")
    log(f"  mean raw coverage = {mean_raw:.3f}   -> {mean_norm:.2f} of the floor->oracle band")
    log(f"  valid submissions = {valids}/{episodes}")
    if mean_norm < LO:
        verdict = (f"FLOORS ({mean_norm:.2f} < {LO}): the live student isn't inferring above the "
                   f"no-inference floor. Dial DOWN — more anchor mass / fewer hidden registers "
                   f"(try --spec tri-2anchor or tri-2anchor-b3).")
    elif mean_norm > HI:
        verdict = (f"MAXES ({mean_norm:.2f} > {HI}): the student is at the oracle — no room for the "
                   f"loop to climb. Dial UP — more hidden registers / a deeper buried cluster "
                   f"(try --spec trap-quad or trap-tri-b4-style coupling).")
    else:
        verdict = (f"IN BAND ({LO} <= {mean_norm:.2f} <= {HI}): live Haiku infers above the floor "
                   f"with headroom below the oracle. {spec.name} is CALIBRATED — proceed to the "
                   f"meta-agent-on-program loop (its own session).")
    log(f"  VERDICT: {verdict}")
    log("=" * 72)
    return {"name": spec.name, "mean_raw": mean_raw, "mean_norm": mean_norm,
            "valid": valids, "episodes": episodes, "verdict": verdict}


def main():
    ap = argparse.ArgumentParser(description="Chapter-2 live-Haiku calibration on a register world")
    ap.add_argument("--backend", choices=["mock", "real"], default="mock")
    ap.add_argument("--spec", default="trap-tri", help="world to calibrate (a threshold candidate)")
    ap.add_argument("--episodes", type=int, default=8, help="live episodes (real runs use ~8 to damp Haiku variance)")
    ap.add_argument("--seed", type=int, default=1234, help="base RNG seed (episode i uses seed+i)")
    ap.add_argument("--task-model", default=None)
    args = ap.parse_args()

    cfg = Config()
    cfg.backend = args.backend
    if args.task_model:
        cfg.task_model = args.task_model
    llm.reset_accounting()
    run(cfg, _spec(args.spec), max(1, args.episodes), args.seed)
    acct = llm.accounting()
    print(f"\ncost: {acct['calls']} claude -p calls, ${acct['cost_usd']:.4f}  by_role={acct['by_role']}")


if __name__ == "__main__":
    main()
