"""The Chapter-2 **model-orchestrated** loop (option B, RESET_DESIGN.md -> "Locked decisions" 2).

This is the reseed's loop: it searches **playbook-space** for the English disposition that makes a
fixed weak student (Haiku) tasteful on the anchor trail world. It reuses the DGM-H spine wholesale
— the archive (`hta.archive`), open-ended parent selection, the Opus self-modify airgap
(`hta.sandbox`) — and swaps the evolved unit and the judge from Chapter 1's:

  * evolved node = **`playbook.md` only** — non-executable English, the player's SYSTEM prompt. The
    meta agent (Opus) rewrites *this*, nothing else (no solver.py; safe-eval lifted). A Haiku TOP
    session natively probes / spawns workers / keeps a scratchpad / submits, confined by the
    probe-MCP airgap (`hta/ch2/probe_server.py`).
  * judge = band-normalized **coverage** (`EpisodeState.score`): the cells the agent's own probes
    pin and it submits correctly, normalized into the model-free floor->oracle band. Outcome-only,
    agent-inaccessible, deterministic — the integrity floor, lifted to coverage.

There is no world-smith yet: the curriculum is the one build-screened anchor spec, and "worlds" are
fresh hidden register draws of it (same public structure, a different buried landmark each). Train
and a disjoint held-out set are both draws, so held-out coverage measures generalization across
unseen instances. References are spec-constant, so the band is identical for both splits.

One iteration mirrors the spine loop: seed gen_0000 (the floor playbook) if empty -> select a parent
-> draw this iteration's worlds -> eval the PARENT -> Opus branches + rewrites its playbook into a
CHILD -> eval the CHILD on the SAME worlds -> score (train + held-out) -> archive.
"""

import json
import os
import random
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple

from .. import llm, sandbox
from ..archive import Archive
from ..config import Config
from . import anchor
from .episode_state import (EpisodeState, canonical_spec, normalize, state_to_env)

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
SEED_DIR = os.path.join(_HERE, "seed")
SOLVED_BAR = 0.85   # norm at/above which a world counts as "reached the oracle" (band ceiling)

# The neutral kickoff carried by -p; the playbook rides as --append-system-prompt (it IS the agent).
KICKOFF = ("Investigate this hidden world now. Start by reading world_map, then probe, spawn "
           "workers, and take notes as your instructions direct, and submit_map once when further "
           "probing is not worth its cost.")

# The one-paragraph, HyperAgents-minimal meta prompt (RESET_DESIGN.md -> "Seed"). It edits the
# playbook ONLY, diagnoses from the trajectory, and NEVER names "taste" — that is our word for what
# the lineage discovers, never the agent's target.
META_INSTRUCTION = """You improve a research agent by editing its playbook.

The agent investigates an unknown world under a scarce probe budget: it can probe cells, deploy
workers with a share of its budget and a task it writes, keep an editable scratchpad, and submit one
reconstruction. Its entire policy is the English in `playbook.md` — that text is its system prompt
(it is read as instructions, never executed). Your only lever is to rewrite that text.

In your workspace:
  - `playbook.md`    : the agent's playbook — the ONLY thing you may change.
  - `EVAL_REPORT.md` : a sanitized record of how it just investigated several worlds — which cells it
                       probed, the workers it deployed, how it kept notes, what it reconstructed, and
                       how much of each world it covered. The hidden world values are NOT given and
                       you must not try to reconstruct them; reason only about the agent's CONDUCT.

Read both. From the trajectory and outcomes alone, infer the single most impactful weakness in how
this agent investigates — where it wasted budget, chased a payoff that paid nothing, lost track of
what it knew, or stopped too early/late. Name the weakness you actually see; do not pattern-match to
a checklist (a fix copied from a template is the designer's judgment re-installed, not the agent's
grown). Then make ONE coherent, evidence-supported change to `playbook.md` that would help any agent
with that weakness — including, when the evidence points there, the note-keeping discipline the
scratchpad should follow. Keep the playbook short and general; prefer how it allocates and tracks
over surface wording. Make the edit now in `playbook.md`. Do not ask questions."""


# ---------------------------------------------------------------------------
# Worlds: fresh hidden register draws of the one anchor spec. Parent and child see the SAME draws
# (a fair comparison); each iteration reseeds so a playbook cannot memorize a specific instance.
# ---------------------------------------------------------------------------
def build_worlds(n_train: int, n_transfer: int, iteration: int):
    spec = canonical_spec()
    base = 10_000 * (iteration + 1)
    train = [(spec, anchor_hstar(spec, base + i)) for i in range(n_train)]
    transfer = [(spec, anchor_hstar(spec, base + 5_000 + i)) for i in range(n_transfer)]
    return train, transfer


def anchor_hstar(spec: anchor.TrailSpec, seed: int) -> Tuple[int, ...]:
    rng = random.Random(seed)
    return tuple(rng.randrange(spec.K) for _ in range(spec.R))


# ---------------------------------------------------------------------------
# One episode: the playbook-driven TOP session investigates ONE world; we score its coverage. Real
# backend runs a live claude session through the probe-MCP airgap; mock runs a deterministic
# floor-player (probe the cheapest coverage cells, submit them) so the loop plumbing is observable
# offline at zero cost — it is NOT a model of taste, only of the wiring.
# ---------------------------------------------------------------------------
def run_episode(playbook: str, spec: anchor.TrailSpec, hstar, cfg: Config, log=print) -> dict:
    if cfg.backend == "mock":
        result = _mock_floor_player(spec, hstar)
    else:
        result = _real_episode(playbook, spec, hstar, cfg, log=log)
    score, _ = score_result(spec, hstar, result)
    return {"result": result, "score": score}


def _mock_floor_player(spec: anchor.TrailSpec, hstar) -> dict:
    st = EpisodeState(spec, hstar)
    walkable = sorted((c for c in st.cov_cols if c in st._probe_set), key=lambda c: st.costs[c])
    for c in walkable:
        if st.costs[c] > st.remaining_cost():
            break
        st.probe(c)
    st.submit_map({e["col"]: e["value"] for e in st.log})
    return st.result()


def _real_episode(playbook: str, spec: anchor.TrailSpec, hstar, cfg: Config, log=print) -> dict:
    fd, result_path = tempfile.mkstemp(prefix="hta_top_", suffix=".json")
    os.close(fd)
    env = state_to_env(spec, hstar, spec.budget)
    env.update({"HTA_ROLE": "top", "HTA_RESULT_PATH": result_path,
                "HTA_BACKEND": cfg.backend, "HTA_TASK_MODEL": cfg.task_model})
    try:
        res = llm.episode(prompt=KICKOFF, model=cfg.task_model,
                          mcp_server_argv=[__import__("sys").executable, "-m", "hta.ch2.probe_server"],
                          server_env=env, cwd=_REPO_ROOT,
                          allowed_tools=cfg.top_allowed_tools, max_turns=cfg.top_max_turns,
                          role="task_episode", cfg=cfg, append_system=playbook)
        if res.get("is_error"):
            log(f"    episode error: {res.get('result')}")
        with open(result_path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log(f"    episode produced no result file ({e}); scoring as empty")
        return {"log": [], "spawns": [], "mem": "", "submitted": {}, "used": 0}
    finally:
        try:
            os.remove(result_path)
        except OSError:
            pass


def score_result(spec: anchor.TrailSpec, hstar, result: dict) -> Tuple[dict, EpisodeState]:
    """Replay a finished episode's log + submission into a fresh state and score it. Pure: the band
    judge is a deterministic f(structure, observations), so the score does not depend on any live
    process — only on which cells were probed and what was submitted."""
    st = EpisodeState(spec, hstar)
    st.log = list(result.get("log", []))
    sub = result.get("submitted") or {}
    st.submitted = {int(k): int(v) for k, v in sub.items()} if sub else None
    st.used = int(result.get("used", 0))
    st.spawns = list(result.get("spawns", []))
    return st.score(), st


# ---------------------------------------------------------------------------
# Evaluate a playbook across worlds -> aggregate band coverage + a SANITIZED report. Real episodes
# are independent claude sessions, so (world x repeat) units run concurrently; mock stays serial and
# deterministic. Aggregation is norm-of-mean (average raw, normalize once) — averaging per-episode
# norms double-counts the [0,1] clamp.
# ---------------------------------------------------------------------------
def evaluate(node_dir: str, worlds: List[tuple], cfg: Config, log=print) -> dict:
    if not worlds:
        return {"mean_raw": 0.0, "mean_norm": 0.0, "solved": 0, "n_worlds": 0,
                "per_world": [], "report_md": "# (no worlds)\n"}
    playbook = _read(os.path.join(node_dir, "playbook.md"), "")
    repeats = max(getattr(cfg, "eval_repeats", 1) or 1, 1)
    concurrency = max(getattr(cfg, "eval_concurrency", 1) or 1, 1)
    units = [i for i in range(len(worlds)) for _ in range(repeats)]
    recs_by_world: dict = {i: [] for i in range(len(worlds))}

    def run_unit(i):
        spec, hstar = worlds[i]
        return i, run_episode(playbook, spec, hstar, cfg, log=log)

    if cfg.backend == "mock" or concurrency <= 1 or len(units) <= 1:
        for i in units:
            recs_by_world[i].append(run_unit(i)[1])
    else:
        with ThreadPoolExecutor(max_workers=min(concurrency, len(units))) as ex:
            for i, rec in ex.map(run_unit, units):
                recs_by_world[i].append(rec)

    spec0 = worlds[0][0]
    floor, oracle = anchor.floor_value(spec0), anchor.oracle_value(spec0)
    per_world = []
    for i in range(len(worlds)):
        recs = recs_by_world[i]
        raw = sum(r["score"]["raw"] for r in recs) / len(recs)
        rec = dict(recs[0])
        rec["score"] = dict(recs[0]["score"])
        rec["score"]["raw"] = round(raw, 4)
        rec["score"]["norm"] = round(normalize(raw, floor, oracle), 4)
        per_world.append(rec)
        s = rec["score"]
        log(f"  world_{i}: raw={s['raw']:.2f} norm={s['norm']:.2f} determined={s['determined']} "
            f"used={s['used']}/{s['budget']}" + ("" if repeats == 1 else f" (avg of {repeats})"))

    mean_raw = sum(r["score"]["raw"] for r in per_world) / len(per_world)
    mean_norm = round(normalize(mean_raw, floor, oracle), 4)
    solved = sum(1 for r in per_world if r["score"]["norm"] >= SOLVED_BAR)
    return {"mean_raw": round(mean_raw, 4), "mean_norm": mean_norm, "solved": solved,
            "n_worlds": len(worlds), "per_world": per_world,
            "report_md": _sanitized_report(per_world, spec0, floor, oracle)}


def _eval_split(node_dir, train, transfer, cfg, log):
    log(" train worlds:")
    tr = evaluate(node_dir, train, cfg, log=log)
    log(" held-out worlds (fresh instances):")
    te = evaluate(node_dir, transfer, cfg, log=log)
    combined = round((tr["mean_norm"] + te["mean_norm"]) / 2.0, 4)
    return {"train": tr, "transfer": te, "combined_fitness": combined}


# ---------------------------------------------------------------------------
# Sanitized report for the meta agent: the agent's OWN conduct (probes chosen, workers deployed,
# scratchpad, reconstruction, coverage) + the PUBLIC structure — never the hidden seed or the true
# values of un-probed cells. So Opus reasons about HOW it investigated, never about the answer.
# ---------------------------------------------------------------------------
def _sanitized_report(per_world: List[dict], spec: anchor.TrailSpec, floor, oracle) -> str:
    lines = [
        "# Coverage evaluation report (sanitized)\n",
        f"The world: a trail of public pointers (trailhead {spec.trailhead} -> waypoints "
        f"{list(spec.waypoints)} -> landmarks {[list(r) for r in spec.landmarks]}) through "
        f"{spec.R} registers (values 0..{spec.K - 1}, the only hidden information). Reading a "
        f"signpost pays ZERO coverage; the clearing blocks pay immediately; the deep valley pays "
        f"only once the trail is walked to its end. Probe budget per world: {spec.budget} (cost-"
        f"weighted). Coverage band (raw cells): floor {floor:.2f} -> oracle {oracle:.2f}.",
        "You are NOT given the register values or the true values of un-probed cells; reason only "
        "about the agent's CONDUCT.\n",
    ]
    for i, r in enumerate(per_world):
        s, res = r["score"], r["result"]
        probes = [e for e in res.get("log", []) if e.get("via") == "self"]
        seq = ", ".join(f"col{e['col']}->{e['value']}(c{e['cost']})" for e in probes) or "(none)"
        lines.append(f"\n## world_{i}")
        lines.append(f"- coverage: {s['norm']:.2f} of the floor->oracle band "
                     f"(raw {s['raw']} cells, {s['determined']} logically determined), "
                     f"budget used {s['used']}/{s['budget']}")
        lines.append(f"- probes by the top (in order): {seq}")
        for j, sp in enumerate(res.get("spawns", [])):
            rep = (sp.get("report") or "").strip().replace("\n", " ")
            lines.append(f"- worker {j}: budget {sp.get('used')} used, {sp.get('n_obs')} cells "
                         f"observed; task={sp.get('task')!r}; report: {rep[:200]}")
        mem = (res.get("mem") or "").strip()
        if mem:
            lines.append(f"- final scratchpad:\n  " + mem.replace("\n", "\n  "))
        sub = res.get("submitted") or {}
        lines.append(f"- reconstruction submitted: {len(sub)} cells")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Meta step: branch the parent node and rewrite its playbook. Real -> Opus through the sandbox
# airgap (Edit/Read/Write, no Bash, never runs the agent against a world). Mock -> a deterministic
# append so the offline plumbing shows a node change.
# ---------------------------------------------------------------------------
def meta_edit(parent_dir: str, child_dir: str, report_md: str, cfg: Config, log=print) -> None:
    if os.path.exists(child_dir):
        shutil.rmtree(child_dir)
    shutil.copytree(parent_dir, child_dir)
    cache = os.path.join(child_dir, "__pycache__")
    if os.path.isdir(cache):
        shutil.rmtree(cache)
    with open(os.path.join(child_dir, "EVAL_REPORT.md"), "w") as f:
        f.write(report_md)
    if cfg.backend == "mock":
        pb = os.path.join(child_dir, "playbook.md")
        with open(pb, "a") as f:
            f.write("\n<!-- (mock) plumbing-stub edit; the real meta agent rewrites this. -->\n")
        log("  meta agent (mock): appended a plumbing-stub line to playbook.md")
        return
    res = sandbox.get_sandbox(cfg).run_meta_edit(child_dir, META_INSTRUCTION, cfg, log=log)
    log(f"  meta agent [{cfg.sandbox}]: turns={res.get('num_turns')} "
        f"error={res.get('is_error')} cost=${res.get('cost_usd', 0):.3f}")


# ---------------------------------------------------------------------------
# One iteration.
# ---------------------------------------------------------------------------
def run_iteration(cfg: Config, iteration: int = 0, log=print) -> dict:
    archive = Archive(cfg.archive_dir)
    rng = random.Random(iteration)

    if archive.is_empty():
        archive.seed(SEED_DIR)
        log("seeded gen_0000 from the floor playbook")

    parent = archive.select_parent(rng, policy=cfg.parent_selection,
                                    novelty_scale=cfg.parent_novelty_scale,
                                    sharpness=cfg.parent_quality_sharpness,
                                    mdl_lambda=cfg.mdl_lambda)
    parent_dir = archive.node_dir(parent)
    log(f"selected parent: gen_{parent:04d} (selection={cfg.parent_selection})")

    train, transfer = build_worlds(cfg.n_train_worlds, cfg.n_transfer_worlds, iteration)
    spec = train[0][0] if train else canonical_spec()
    log(f"world: {spec.name}  R={spec.R} K={spec.K} budget={spec.budget}  "
        f"({len(train)} train + {len(transfer)} held-out draws)")

    log("\n[evaluate PARENT]")
    parent_eval = _eval_split(parent_dir, train, transfer, cfg, log=log)

    log("\n[meta agent: branch + rewrite playbook]")
    genid = archive.next_genid()
    child_dir = archive.node_dir(genid)
    meta_edit(parent_dir, child_dir, parent_eval["train"]["report_md"], cfg, log=log)

    log("\n[evaluate CHILD]")
    try:
        child_eval = _eval_split(child_dir, train, transfer, cfg, log=log)
        valid = True
    except Exception as e:  # a broken playbook must score, not crash the loop
        log(f"child failed to evaluate: {e}")
        child_eval = {"train": {"mean_norm": 0.0, "solved": 0},
                      "transfer": {"mean_norm": 0.0, "solved": 0}, "combined_fitness": 0.0}
        valid = False

    summary = {
        "fitness": child_eval["combined_fitness"],
        "train_fitness": child_eval["train"]["mean_norm"],
        "transfer_fitness": child_eval["transfer"]["mean_norm"],
        "solved_train": child_eval["train"]["solved"],
        "solved_transfer": child_eval["transfer"]["solved"],
        "valid": valid, "spec": spec.name,
        "program_size": None,  # the node is English, not code -> no MDL-on-program penalty (staged)
    }
    archive.add(genid, parent, summary)

    return {"parent": parent, "child": genid,
            "parent_fitness": parent_eval["combined_fitness"],
            "child_fitness": child_eval["combined_fitness"],
            "improved": child_eval["combined_fitness"] > parent_eval["combined_fitness"],
            "parent_norm": (parent_eval["train"]["mean_norm"], parent_eval["transfer"]["mean_norm"]),
            "child_norm": (child_eval["train"]["mean_norm"], child_eval["transfer"]["mean_norm"]),
            "valid_child": valid}


def _read(path, default=""):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return default
