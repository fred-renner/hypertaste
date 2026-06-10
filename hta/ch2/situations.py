"""The **situation harness** (PLAN.md -> design lock 8): a situation is a constructed
mid-episode state — a partial map (prefix probes already spent), a scratchpad, and a remaining
budget — cheap, deterministic, targeted at one trigger. It is the lab's third instrument, next
to the full episode (the exam) and the model-free screen:

  * the world-smith's ZPD checks against the *live* champion (Pass 5) — "does the champion fire
    the right move from THIS state" is one cheap episode, not a full eval;
  * fast filtering of meta-edits before they earn a full eval (staged eval, the cost guard);
  * the validation battery (the demoted hand virtue list lives OUTSIDE the loop, checked here).

Full hidden-map episodes remain the exam — context/memory pressure only exists there, and a
procedure tuned only on a situation library would overfit the library (the lock's own caveat).

Mechanics: the prefix probes are REPLAYED through the ordinary `EpisodeState.probe` (charging
their cost, populating the log, refining the belief — the judge then counts them like any other
observation), and the scratchpad is pre-seeded — the only memory a resumed live session has of
the prefix, exactly as the carried artifact is the only memory a lineage has. Live, the
situation rides to the probe server in `HTA_SITUATION` (applied by `state_from_env`); the player
is told only to resume. Scoring is band-normalized against the SITUATION's own ceiling: the
exact best-play continuation from the constructed belief with the remaining budget
(`situation_band`), with the floor at what the prefix alone already pins — so 0 means "added
nothing", 1 means "played the remainder optimally"."""

import json
from dataclasses import dataclass
from typing import Optional, Tuple

from . import anchor
from .episode_state import EpisodeState, normalize


@dataclass(frozen=True)
class Situation:
    """One constructed mid-episode state. `remaining` is the budget the player has left; the
    episode budget materializes as prefix cost + remaining (None => whatever the spec's budget
    leaves after the prefix)."""
    name: str
    spec: object
    hstar: Tuple[int, ...]
    probed: Tuple[int, ...] = ()
    mem: str = ""
    remaining: Optional[int] = None

    def episode_budget(self) -> int:
        _, cells, costs, _, _ = anchor.build_tableau(self.spec)
        prefix = sum(costs[c] for c in self.probed)
        if self.remaining is None:
            return self.spec.budget
        return prefix + int(self.remaining)

    def to_dict(self) -> dict:
        return {"name": self.name, "spec": self.spec.to_dict(), "hstar": list(self.hstar),
                "probed": list(self.probed), "mem": self.mem, "remaining": self.remaining}

    @classmethod
    def from_dict(cls, d: dict) -> "Situation":
        from .episode_state import spec_from_dict
        return cls(name=d["name"], spec=spec_from_dict(d["spec"]), hstar=tuple(d["hstar"]),
                   probed=tuple(d.get("probed", ())), mem=d.get("mem", ""),
                   remaining=d.get("remaining"))


def materialize(sit: Situation) -> EpisodeState:
    """Build the mid-episode state offline: replay the prefix through the ordinary probe path
    (cost charged, log populated, belief refined), seed the scratchpad."""
    st = EpisodeState(sit.spec, sit.hstar, budget=sit.episode_budget())
    for col in sit.probed:
        r = st.probe(int(col))
        if r.get("error"):
            raise ValueError(f"situation {sit.name!r}: bad prefix probe {col}: {r['error']}")
    if sit.mem:
        st.mem = sit.mem
    return st


def to_env(sit: Situation) -> dict:
    """The live ride: the ordinary world env plus the situation payload `state_from_env`
    applies server-side. The hidden seed stays on the server channel, as ever."""
    from .episode_state import state_to_env
    env = state_to_env(sit.spec, sit.hstar, sit.episode_budget())
    env["HTA_SITUATION"] = json.dumps({"probed": list(sit.probed), "mem": sit.mem})
    return env


SITUATION_KICKOFF = (
    "You are resuming a partially complete investigation of this hidden world: your scratchpad "
    "(mem_read) holds what has been established so far, and some budget is already spent — "
    "remaining() shows what is left. Read world_map and your notes, then continue as your "
    "instructions direct, and submit_map once when further probing is not worth its cost.")


# ---------------------------------------------------------------------------
# The situation band: floor = what the prefix alone already pins (a do-nothing continuation),
# ceiling = the exact best-play continuation from the constructed belief with the remaining
# budget. Same dumb-deterministic machinery as the spec-level band, conditioned on the state.
# ---------------------------------------------------------------------------
def score_situation(sit: Situation, result: dict) -> dict:
    """Score a finished situation episode: replay the full log + submission (prefix included),
    then normalize the earned coverage into the situation's own floor->ceiling band."""
    st = EpisodeState(sit.spec, sit.hstar, budget=sit.episode_budget())
    st.log = list(result.get("log", []))
    sub = result.get("submitted") or {}
    st.submitted = {int(k): int(v) for k, v in sub.items()} if sub else None
    st.used = int(result.get("used", 0))
    st.spawns = list(result.get("spawns", []))

    pre = materialize(sit)
    H0 = pre.observed_belief()
    floor = float(anchor.determined(pre.table, pre.cov_cols, H0))
    ceiling = _best_play_from(pre, H0, pre.remaining_cost())
    raw = st.coverage_raw()
    return {"raw": raw, "floor": floor, "ceiling": round(ceiling, 4),
            "norm": round(normalize(raw, floor, ceiling), 4),
            "used": st.used, "budget": st.budget, "situation": sit.name}


def _best_play_from(st: EpisodeState, H0, budget: int) -> float:
    """Exact best-play continuation (the belief-MDP, anchor-style) from an arbitrary belief —
    the situation's ceiling. Dumb, deterministic, token-free."""
    table, costs, cov, probe = st.table, st.costs, st.cov_cols, st.probe_cols

    memo = {}

    def V(H, b):
        key = (H, b)
        if key in memo:
            return memo[key]
        best = float(anchor.determined(table, cov, H))
        for c in probe:
            if costs[c] > b:
                continue
            groups = anchor._partition(table, H, c)
            if len(groups) == 1:
                continue
            exp = sum(len(g) / len(H) * V(g, b - costs[c]) for g in groups.values())
            if exp > best:
                best = exp
        memo[key] = best
        return best

    return V(H0, budget)


# ---------------------------------------------------------------------------
# Running one situation. Mock = the deterministic wiring player (spend the remaining budget on
# the cheapest probes, submit what the whole log pins); real = a live confined session resumed
# from the constructed state.
# ---------------------------------------------------------------------------
def run_situation(playbook: str, sit: Situation, cfg, log=print) -> dict:
    if cfg.backend == "mock":
        st = materialize(sit)
        finish_with_inference(st)
        result = st.result()
    else:
        from . import loop
        result = loop._real_episode(
            playbook, sit.spec, sit.hstar, cfg, log=log,
            extra_env={"HTA_SITUATION": json.dumps({"probed": list(sit.probed),
                                                    "mem": sit.mem})},
            kickoff=SITUATION_KICKOFF, budget=sit.episode_budget())
    return {"result": result, "score": score_situation(sit, result)}


def finish_with_inference(st: EpisodeState) -> None:
    """The deterministic mock continuation: probe the cheapest still-affordable cells, then
    submit every coverage cell the log logically pins. Wiring, not taste."""
    for c in sorted(st.probe_cols, key=lambda c: (st.costs[c], c)):
        if c in {e["col"] for e in st.log}:
            continue
        if st.costs[c] > st.remaining_cost():
            break
        st.probe(c)
    H = st.observed_belief()
    rep = next(iter(H))
    st.submit_map({c: st.table[rep][c] for c in st.cov_cols
                   if all(st.table[h][c] == st.table[rep][c] for h in H)})
