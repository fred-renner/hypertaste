"""Instance 0 — the inner-loop proof of principle (PLAN.md -> record v2, "The proof of principle";
`PASS3_REDO.md` §7). The smallest honest test of the core bet: *does a grown playbook beat the best
day-one playbook on fresh machines, same weak student, same body?*

Three players, paired on the same held-out draws (fresh machines):

  1. **bare**     — the weak student (Haiku) with no playbook: the floor, a sanity check that a
                    playbook is net-positive at all.
  2. **day-one**  — the **smart-spec null** (PLAN.md §4): the best playbook the lab's strongest model
                    (Opus) writes blind, from the rules of the game alone, frozen.
  3. **coached**  — day-one, then rewritten by Opus from the day-one player's *conduct* on a disjoint
                    train set (a few rounds). The product: English grown by watching the student fail.

The signal sought: **coached > day-one on fresh machines.** If it shows, the loop closes; if not, the
core bet is in trouble — and we learned it for a few dollars before furnishing the house.

The two invariants hold: scoring is the dumb deterministic exam (`machine.score_models`), and the
evolved artifact is the playbook *text* — the coach (Opus, via `llm.complete`, no tools, fed only the
sanitized conduct + the public rules) never sees the hidden machine and never executes anything.
"""

import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from .. import llm
from ..config import Config
from .machine import Blueprint, draw_machine
from .machine_state import machine_to_env

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))

# ---------------------------------------------------------------------------
# Instance 0 — the one hand-authored blueprint (the build-screened pick, run_instance0.py --screen).
# 8 outputs of medium domain over a tight budget: a flat smear resolves nothing, so the winning move
# is to read each output's kind and CONCENTRATE — extrapolate the cheap affines, fully read the
# affordable tables, and abstain on the rest. Scripted floor ~0.18, tasteful reference ~0.32.
# ---------------------------------------------------------------------------
def instance0() -> Blueprint:
    return Blueprint(name="inst0",
                     slots=((10, 3), (10, 2), (9, 2), (9, 1), (10, 3), (9, 2), (8, 3), (8, 1)),
                     budget=13, p_affine=0.2, p_const=0.15)


# The neutral kickoff carried by -p; the playbook rides as --append-system-prompt (it IS the agent).
KICKOFF = ("Investigate this hidden machine now. Start by calling machine_map, then probe outputs, "
           "take notes with mem_patch as your instructions direct, and call submit once with a model "
           "for every output when further probing is not worth its cost.")

# The rules of the game, in the generic interface (no world-story) — shared by the day-one author and
# the coach so both reason from the same public contract the player sees.
WORLD_BRIEF = """The agent investigates a hidden MACHINE under a scarce probe budget, then is graded on an exam.

The body (its tools):
  - machine_map(): the public rules. Several OUTPUTS; each reads an integer for a scalar INPUT you
    set (an integer in [0, domain)). Each output lists its `domain` and its `weight` (points per
    question). Each output's law is ONE of: a constant; an affine map a*input+b (a steady step you
    can extrapolate from a few reads); or an arbitrary lookup table (predictable only where you have
    read it). WHICH law, and its parameters, are HIDDEN.
  - probe(output, input): read one value. Costs ONE budget unit and earns NOTHING toward the score.
  - remaining(): budget left.  mem_read()/mem_patch(): an editable scratchpad.
  - submit(models): end the episode with one model per output.

Scoring (only the exam pays):
  - You are graded on the FULL input domain of EVERY output, including inputs you never probed.
  - A correct general law (a right affine, or a fully read table) earns full weight on every question.
  - Abstaining on an output earns a small blind-guess credit (the strongest fixed guess) — so on an
    output you cannot resolve within budget, abstaining is the CORRECT move.
  - A committed WRONG value earns ZERO (worse than abstaining). Probing earns nothing.
  - The budget is far smaller than reading everything, so a thin smear across all outputs resolves
    none of them."""


# ---------------------------------------------------------------------------
# The lab roles (Opus): author the day-one playbook, then coach it from conduct. Both use the
# constrained `complete` seam (no tools) and return the playbook TEXT — the evolved artifact.
# ---------------------------------------------------------------------------
_CAP_WORDS = 300

AUTHOR_INSTRUCTION = f"""You are writing the day-one PLAYBOOK for a weak research agent — the English that will be its
entire operating procedure (its system prompt; read as instructions, never executed). It faces the
world below, fresh and different every episode, and you will NOT see it play. Write the best general
procedure you can from the rules alone.

{{brief}}

Write the playbook now: concise, general, at most {_CAP_WORDS} words, addressed to the agent ("you").
Tell it HOW to spend a scarce budget and HOW to decide each output's model. Do not invent tools it
does not have. Output ONLY the playbook text, no preamble, no code fences."""

COACH_INSTRUCTION = f"""You improve a weak research agent by rewriting its PLAYBOOK — the English that is its entire
operating procedure (its system prompt; read as instructions, never executed). Your ONLY lever is
that text.

The world it faces (the public rules; fresh and different every episode):
{{brief}}

Its CURRENT playbook:
---
{{playbook}}
---

A sanitized record of how it just investigated several fresh machines (its CONDUCT and outcomes only
— never the hidden laws; do not try to reconstruct them):
---
{{report}}
---

From the conduct and outcomes alone, find the SINGLE most impactful weakness in how this agent
allocates its budget and decides each output's model — where it wasted probes, committed a wrong
model it should have abstained on, smeared instead of concentrating, or abstained on something it
could have resolved. Name the weakness you actually see; do not pattern-match to a checklist. Then
make ONE coherent, evidence-supported rewrite of the playbook that would help any agent with that
weakness. Keep it concise and general (at most {_CAP_WORDS} words), addressed to the agent ("you").
Output ONLY the new playbook text, no preamble, no code fences."""


def author_day_one(cfg: Config, log=print) -> str:
    if cfg.backend == "mock":
        return _MOCK_DAY_ONE
    txt = llm.complete(AUTHOR_INSTRUCTION.format(brief=WORLD_BRIEF),
                       model=cfg.world_model, role="author", cfg=cfg)
    log(f"  day-one playbook authored ({len(txt.split())} words)")
    return txt.strip()


def coach(playbook: str, report_md: str, cfg: Config, log=print) -> str:
    if cfg.backend == "mock":
        return playbook + "\n\n(coached: concentrate budget; abstain on the unresolved.)"
    txt = llm.complete(COACH_INSTRUCTION.format(brief=WORLD_BRIEF, playbook=playbook, report=report_md),
                       model=cfg.world_model, role="coach", cfg=cfg)
    log(f"  playbook coached ({len(txt.split())} words)")
    return txt.strip()


# ---------------------------------------------------------------------------
# One episode: the playbook-driven player investigates ONE machine; we score its submission.
# ---------------------------------------------------------------------------
def run_episode(playbook: str, machine, cfg: Config, log=print) -> dict:
    if cfg.backend == "mock":
        result = _mock_player(machine)
    else:
        result = _real_episode(playbook, machine, cfg, log=log)
    from .machine import score_models
    score = score_models(machine, result.get("submitted") or {})
    return {"result": result, "score": score}


def _real_episode(playbook: str, machine, cfg: Config, log=print) -> dict:
    fd, result_path = tempfile.mkstemp(prefix="hta_machine_", suffix=".json")
    os.close(fd)
    env = machine_to_env(machine)
    env.update({"HTA_RESULT_PATH": result_path, "HTA_BACKEND": cfg.backend,
                "HTA_TASK_MODEL": cfg.task_model})
    allowed = ("mcp__probe__probe", "mcp__probe__remaining", "mcp__probe__machine_map",
               "mcp__probe__mem_read", "mcp__probe__mem_patch", "mcp__probe__submit")
    try:
        res = llm.episode(prompt=KICKOFF, model=cfg.task_model,
                          mcp_server_argv=[__import__("sys").executable, "-m", "hta.ch2.machine_server"],
                          server_env=env, cwd=_REPO_ROOT, allowed_tools=allowed,
                          max_turns=cfg.top_max_turns, role="task_episode", cfg=cfg,
                          append_system=(playbook or None))
        if res.get("is_error"):
            log(f"    episode error: {res.get('result')}")
        with open(result_path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log(f"    episode produced no result file ({e}); scoring as empty")
        return {"log": [], "mem": "", "submitted": {}, "used": 0}
    finally:
        try:
            os.remove(result_path)
        except OSError:
            pass


def _mock_player(machine) -> dict:
    """A deterministic offline player so the whole pipeline runs at zero cost. NOT a model of taste —
    a fixed policy that scouts each output, extrapolates a clean line, enumerates the small tables it
    can afford, and abstains otherwise, just so the plumbing (probe -> submit -> score) is observable.
    """
    from .machine_state import MachineEpisode
    ep = MachineEpisode(machine)
    n = len(machine.outputs)
    order = sorted(range(n), key=lambda i: (-machine.outputs[i].weight, machine.outputs[i].domain))
    models = {}
    for i in order:
        o = machine.outputs[i]
        seen = {}
        for x in range(min(3, o.domain)):
            r = ep.probe(i, x)
            if r.get("value") is None:
                break
            seen[x] = r["value"]
        if len(seen) < 2:
            models[i] = {"law": "abstain"}
            continue
        vals = [seen[x] for x in sorted(seen)]
        xs = sorted(seen)
        if len(set(vals)) == 1:
            models[i] = {"law": "const", "c": vals[0]}
        elif (vals[1] - vals[0]) * (xs[2] - xs[0] if len(xs) > 2 else 1) == \
             (vals[-1] - vals[0]) * (xs[1] - xs[0]) and (xs[1] - xs[0]):
            a = (vals[1] - vals[0]) // (xs[1] - xs[0])
            models[i] = {"law": "affine", "a": a, "b": vals[0] - a * xs[0]}
        else:
            need = [x for x in range(o.domain) if x not in seen]
            if len(need) <= ep.remaining_budget():
                for x in need:
                    r = ep.probe(i, x)
                    if r.get("value") is not None:
                        seen[x] = r["value"]
            models[i] = {"law": "table", "values": {str(x): v for x, v in seen.items()}}
    ep.mem = "(mock player notes)"
    ep.submit(models)
    return ep.result()


# ---------------------------------------------------------------------------
# Evaluate a playbook across machines -> mean band score + a SANITIZED conduct report (for the coach).
# ---------------------------------------------------------------------------
def evaluate(playbook: str, machines: List, cfg: Config, log=print, label: str = "") -> dict:
    concurrency = max(getattr(cfg, "eval_concurrency", 1) or 1, 1)

    def run_unit(j):
        return j, run_episode(playbook, machines[j], cfg, log=log)

    recs: List[Optional[dict]] = [None] * len(machines)
    if cfg.backend == "mock" or concurrency <= 1 or len(machines) <= 1:
        for j in range(len(machines)):
            recs[j] = run_unit(j)[1]
    else:
        with ThreadPoolExecutor(max_workers=min(concurrency, len(machines))) as ex:
            for j, rec in ex.map(run_unit, range(len(machines))):
                recs[j] = rec

    norms = [r["score"]["norm"] for r in recs]
    mean_norm = round(sum(norms) / len(norms), 4) if norms else 0.0
    for j, r in enumerate(recs):
        s = r["score"]
        log(f"    {label}world_{j}: norm={s['norm']:+.3f} (raw {s['raw']}/{s['perfect']}, "
            f"blind {s['blind']}, used {r['result'].get('used', 0)}/{machines[j].budget})")
    return {"mean_norm": mean_norm, "per_world": recs,
            "report_md": _sanitized_report(machines, recs)}


def _sanitized_report(machines: List, recs: List[dict]) -> str:
    """The agent's OWN conduct (probes spent per output, scratchpad, the model it submitted, and the
    credit it earned vs perfect/blind) + the PUBLIC structure — never the hidden laws or the true
    value of an output. So the coach reasons about HOW it investigated, never about the answer."""
    lines = ["# Conduct report (sanitized) — how the agent investigated several fresh machines\n",
             "Probing earns nothing; only the held-out exam pays. norm: 0 = lazy/all-abstain, "
             "1 = perfect; negative = confident wrong guessing did worse than abstaining.\n"]
    for j, (m, r) in enumerate(zip(machines, recs)):
        s, res = r["score"], r["result"]
        log_entries = res.get("log", [])
        probes_by_out = {}
        for e in log_entries:
            probes_by_out[e["output"]] = probes_by_out.get(e["output"], 0) + 1
        lines.append(f"\n## machine_{j}: norm {s['norm']:+.3f}  (raw {s['raw']}/{s['perfect']}, "
                     f"blind {s['blind']}, budget used {res.get('used', 0)}/{m.budget})")
        for po in s["per_output"]:
            i = po["output"]
            lines.append(
                f"- output {i}: domain {po['domain']}, weight {po['weight']}, probes spent "
                f"{probes_by_out.get(i, 0)}; submitted '{po['law']}'; earned {po['earned']}/"
                f"{po['perfect']} (blind {po['blind']}) — {po['correct']} right, {po['wrong']} wrong, "
                f"{po['abstain']} abstained")
        mem = (res.get("mem") or "").strip()
        if mem:
            lines.append("- final scratchpad:\n  " + mem.replace("\n", "\n  "))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The proof of principle: author day-one -> coach on train draws -> eval bare/day-one/coached on
# held-out draws (paired, fresh machines). Returns the three mean norms + the artifacts.
# ---------------------------------------------------------------------------
def run_instance0(cfg: Config, n_train: int = 3, n_holdout: int = 5,
                  coaching_rounds: int = 1, seed: int = 0, log=print) -> dict:
    bp = instance0()
    base = 1000 * (seed + 1)
    train = [draw_machine(bp, base + i) for i in range(n_train)]
    holdout = [draw_machine(bp, base + 500 + i) for i in range(n_holdout)]

    log("\n[author the day-one playbook (smart-spec null)]")
    day_one = author_day_one(cfg, log=log)

    log("\n[coach: run day-one on train draws, then rewrite from its conduct]")
    playbook = day_one
    coach_history = []
    for rnd in range(max(coaching_rounds, 0)):
        log(f"  coaching round {rnd + 1}: evaluating current playbook on {n_train} train draws")
        tr = evaluate(playbook, train, cfg, log=log, label="train ")
        new_playbook = coach(playbook, tr["report_md"], cfg, log=log)
        coach_history.append({"round": rnd + 1, "train_norm": tr["mean_norm"],
                              "report_md": tr["report_md"], "playbook": new_playbook})
        playbook = new_playbook
    coached = playbook

    log(f"\n[held-out eval on {n_holdout} fresh draws — paired, three players]")
    log("  bare student (no playbook):")
    bare_eval = evaluate("", holdout, cfg, log=log, label="bare ")
    log("  day-one playbook:")
    day_one_eval = evaluate(day_one, holdout, cfg, log=log, label="dayone ")
    log("  coached playbook:")
    coached_eval = evaluate(coached, holdout, cfg, log=log, label="coached ")

    return {
        "blueprint": bp.to_dict(),
        "bare_norm": bare_eval["mean_norm"],
        "day_one_norm": day_one_eval["mean_norm"],
        "coached_norm": coached_eval["mean_norm"],
        "gap_coached_minus_dayone": round(coached_eval["mean_norm"] - day_one_eval["mean_norm"], 4),
        "day_one_playbook": day_one, "coached_playbook": coached,
        "coach_history": coach_history,
        "holdout_evals": {"bare": bare_eval, "day_one": day_one_eval, "coached": coached_eval},
    }


# A canned day-one playbook for the mock backend (so the offline pipeline is deterministic).
_MOCK_DAY_ONE = (
    "Read machine_map first. Spend your scarce budget where it pays: for each output, probe a few "
    "inputs to learn its kind. If the reads form a steady step, submit an affine and move on. If they "
    "are all equal, submit a constant. If they look arbitrary and the domain is small enough to read "
    "fully within your remaining budget, read it all and submit a table; otherwise abstain rather than "
    "guess. Do not smear your budget thinly across every output.")
