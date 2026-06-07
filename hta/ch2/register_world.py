"""The live student plane for the Chapter-2 **register world** (`threshold.LinkSpec`).

`threshold.py` settled the world's difficulty model-free (the belief-MDP oracle beats every
articulable heuristic on `trap-tri`). The one thing model-free compute cannot tell us is where
the *live student* lands — difficulty calibrates to Haiku, never a proxy (Chapter 1's paid
lesson). This module is that path: it realizes one `LinkSpec` into a flat tape of cell colors,
runs a single live `claude -p` episode over the SAME narrow probe channel the tape world uses
(`hta.ch2.probe_server`, reused unchanged — a register world realized into cells *is* a tape),
and scores the reconstruction by **coverage** normalized into the model-free floor->oracle band.

The integrity floor is intact: the hidden seed is the register assignment, exposed only through
the probe server's env (the airgap); scoring is the same dumb deterministic `f(truth, recon)`;
the references come straight from `threshold.py` (floor / belief-MDP oracle), no LLM judge.

What is PUBLIC (in the prompt) vs HIDDEN (probed): the cell->register formulas are public — the
world map is known, exactly as the tape's pattern family is known. Only the register *values*
are hidden (K**R hypotheses). The prompt is deliberately NEUTRAL (no taste recipe): we are
measuring the blank-slate student, so a floored or maxed reading is a real signal about the
world, not about how much strategy we handed over.
"""

import json
import os
import random
import sys
import tempfile
import uuid
from functools import lru_cache
from typing import List, Optional, Tuple

from .. import llm
from ..config import Config
from . import threshold
from .threshold import LinkSpec

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ALLOWED_TOOLS = ("mcp__probe__probe", "mcp__probe__remaining", "mcp__probe__submit_map")


# ---------------------------------------------------------------------------
# Realize a LinkSpec into the concrete world the student probes.
# ---------------------------------------------------------------------------
def realize(spec: LinkSpec, rng: random.Random) -> Tuple[Tuple[int, ...], List[int]]:
    """Draw a hidden register assignment (the seed) and expand it through the fixed cell
    layout into a flat list of M cell colors — the 'tape' the probe server serves. Uniform
    over registers, matching the prior the floor/oracle references average against."""
    regs = tuple(rng.randrange(spec.K) for _ in range(spec.R))
    cells = [threshold.cell_value(co, c, regs, spec.K) for (co, c) in spec.cells()]
    return regs, cells


# ---------------------------------------------------------------------------
# References (model-free, agent-inaccessible) — the floor->oracle band, in raw coverage.
# ---------------------------------------------------------------------------
def _raw_from_determined(det: float, K: int, M: int) -> float:
    """Raw coverage of a player that nails `det` cells for sure and guesses the rest at 1/K.
    The same bracket the tape world uses (hta/ch2/world.py), so floor/oracle are comparable."""
    return det / M + (1.0 / K) * (1 - det / M)


def references(spec: LinkSpec) -> dict:
    """floor / best-articulable-heuristic / belief-MDP oracle, as both determined cells and raw
    coverage. The band the live student is placed in is floor_raw -> oracle_raw."""
    K, M = spec.K, spec.M
    floor_det = threshold.floor_value(spec)
    oracle_det = threshold.oracle_value(spec)
    heur_dets = {n: threshold._simulate(spec, p) for n, p in threshold.BASKET.items()}
    heur_dets["lookahead2"] = threshold.lookahead_value(spec, depth=2)
    best_heur_det = max(heur_dets.values())
    return {
        "M": M, "K": K, "budget": spec.budget,
        "floor_det": floor_det, "oracle_det": oracle_det, "best_heur_det": best_heur_det,
        "floor_raw": _raw_from_determined(floor_det, K, M),
        "oracle_raw": _raw_from_determined(oracle_det, K, M),
        "best_heur_raw": _raw_from_determined(best_heur_det, K, M),
    }


def normalize(raw: float, ref: dict) -> float:
    """Where raw coverage sits in the floor->oracle band, clamped [0,1]. 0 = no-inference
    floor, 1 = the belief-MDP oracle. The headroom check lives between."""
    denom = ref["oracle_raw"] - ref["floor_raw"]
    return 0.0 if denom <= 1e-9 else max(0.0, min(1.0, (raw - ref["floor_raw"]) / denom))


def score(true_cells: List[int], recon: Optional[List[int]], ref: dict) -> dict:
    """Coverage = fraction of cells correct, plus where it lands in the band. Dumb, deterministic,
    agent-inaccessible — the integrity floor, lifted to coverage."""
    M = ref["M"]
    r = recon or []
    correct = sum(1 for i in range(M) if i < len(r) and r[i] == true_cells[i])
    raw = correct / M
    return {"raw": raw, "norm": normalize(raw, ref), "correct": correct, "M": M,
            "valid": bool(recon) and len(r) == M}


# ---------------------------------------------------------------------------
# The episode prompt — NEUTRAL (no taste recipe). Describes the public world map (the cell
# formulas) and the task; the register values stay hidden behind the probe channel.
# ---------------------------------------------------------------------------
def _cell_formula(coeffs: Tuple[int, ...], const: int, K: int) -> str:
    terms = []
    for r, a in enumerate(coeffs):
        if a == 0:
            continue
        terms.append(f"r{r}" if a == 1 else f"{a}*r{r}")
    if const:
        terms.append(str(const))
    body = " + ".join(terms) if terms else "0"
    return f"({body}) mod {K}"


def build_prompt(spec: LinkSpec) -> str:
    cells = spec.cells()
    lines = [f"  cell {c}: {_cell_formula(co, k, spec.K)}" for c, (co, k) in enumerate(cells)]
    formulas = "\n".join(lines)
    return f"""\
You are reconstructing {spec.M} hidden cells, indexed 0..{spec.M - 1}. Each cell holds an
integer color in 0..{spec.K - 1}.

Every cell's color is a FIXED, KNOWN function of {spec.R} hidden registers r0..r{spec.R - 1}.
Each register is an unknown integer in 0..{spec.K - 1}. The per-cell formulas (the world map,
known to you) are:
{formulas}

You do NOT know the register values — that is the only hidden information. Probing a cell
reveals just that cell's color (its formula evaluated at the true registers, mod {spec.K}).
Deduce the registers from what you probe, then compute every cell.

You have {spec.budget} probes total — far fewer than {spec.M} cells — so you cannot read every
cell; you must infer the rest. Tools:
  - probe(index): reveal one cell's color; returns the value and probes remaining.
  - submit_map(values): submit a JSON array of {spec.M} integers (one color per cell, in
    order). Ends the episode. You MUST call this exactly once before finishing.
Your goal is to maximize the number of the {spec.M} cells you predict correctly.
Act through tools only; emit no prose between tool calls.
"""


# ---------------------------------------------------------------------------
# Mock solver (free): deterministic plumbing/scorer check. Probes the first `budget` cells and
# guesses 0 elsewhere — a no-inference walker, so the mock path lands near the floor by design.
# NOT a claim about Haiku; that is real_solve below.
# ---------------------------------------------------------------------------
def mock_solve(spec: LinkSpec, true_cells: List[int]) -> List[int]:
    recon = [0] * spec.M
    for i in range(min(spec.budget, spec.M)):
        recon[i] = true_cells[i]
    return recon


# ---------------------------------------------------------------------------
# Real single-session episode (one claude -p session; the realized cells served as the tape).
# ---------------------------------------------------------------------------
def real_solve(spec: LinkSpec, true_cells: List[int], cfg: Config, log=print) -> Optional[List[int]]:
    traj = os.path.join(tempfile.gettempdir(), f"hta_reg_{uuid.uuid4().hex}.jsonl")
    open(traj, "w").close()
    server_env = {
        "HTA_TAPE": json.dumps(list(true_cells)),
        "HTA_BUDGET": str(spec.budget),
        "HTA_TRAJ_PATH": traj,
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONPATH": _REPO_ROOT + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    argv = [sys.executable, "-m", "hta.ch2.probe_server"]
    res = llm.episode(build_prompt(spec), model=cfg.task_model, mcp_server_argv=argv,
                      server_env=server_env, cwd=_REPO_ROOT, allowed_tools=_ALLOWED_TOOLS,
                      max_turns=spec.budget * 3 + 12, role="ch2_calib", cfg=cfg)
    if res.get("is_error"):
        log(f"    episode error: {str(res.get('result'))[:120]}")
    recon = _read_recon(traj)
    try:
        os.remove(traj)
    except OSError:
        pass
    return recon


def _read_recon(path: str) -> Optional[List[int]]:
    recon = None
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("type") == "submit":
                    recon = rec.get("values")
    except OSError:
        pass
    return recon


def solve(spec: LinkSpec, true_cells: List[int], cfg: Config, log=print) -> Optional[List[int]]:
    """Dispatch: mock = deterministic no-inference walker; real = live Haiku episode."""
    if cfg.backend == "mock":
        return mock_solve(spec, true_cells)
    return real_solve(spec, true_cells, cfg, log=log)


# ---------------------------------------------------------------------------
# The HARNESS substrate for the meta-agent-on-program loop.
#
# The unit of taste is NOT a prompt, and NOT a fixed probe loop the harness hardcodes — it is the
# task-agent PROGRAM, and that program is itself a *harness*: it deploys one or more airgapped
# claude-agent sessions (each with limited tool use — the probe channel) over the world,
# coordinates them in Python, and assembles a reconstruction. The meta agent rewrites that harness,
# so the loop searches AGENT-ARCHITECTURE space: one agent or many, single-shot or decomposed by
# block, with or without a Python post-solve. Nothing here fixes the call shape — that is the
# meta agent's to discover (its whole job).
#
# AgentContext is the capability handed to the program. world_map() is public; the probe budget is
# global across every agent the program spawns; observations accumulate. The world is reachable
# ONLY by spawning an agent session (run_agent) — computation (e.g. solving the affine system from
# gathered observations) is free Python, but *probing* always goes through an agent over the narrow
# probe channel, so the integrity floor is intact.
#
# Airgap on the spawned agents: probe/remaining/submit_map only (plus an explicit whitelist of
# extra tools); Bash/Read/Edit/Write are denied by llm.episode. Hierarchy is the Python program
# spawning several probe-only sessions — NOT claude's Task tool, which would spawn general agents
# able to read the world source. (Under --sandbox docker, with no world source in the container,
# broader tools become safe.)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _refs_cached(spec: LinkSpec) -> dict:
    """references(spec) is spec-constant and runs a belief-MDP value iteration; cache it so a
    multi-world eval doesn't recompute the same floor/oracle band per instance."""
    return references(spec)


class RegisterWorld:
    """One realized instance of a LinkSpec: a hidden register draw expanded to cell colors, plus
    the model-free references (the floor->oracle band) coverage is normalized against. Built from
    (spec, seed) so train/held-out worlds are reproducible instances of the SAME calibrated spec
    — references are spec-constant, so the only thing the seed varies is which world is hidden."""

    def __init__(self, spec: LinkSpec, seed: int):
        self.spec = spec
        self.seed = seed
        self.regs, self.cells = realize(spec, random.Random(seed))
        self.ref = _refs_cached(spec)

    def score(self, recon: Optional[List[int]]) -> dict:
        return score(self.cells, recon, self.ref)


def _parse_agent_traj(path: str):
    """Read one spawned agent's probe records + final submission from the probe server's log."""
    probes, submission = [], None
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("type") == "probe":
                    probes.append((rec.get("index"), rec.get("value"), bool(rec.get("charged"))))
                elif rec.get("type") == "submit":
                    submission = rec.get("values")
    except OSError:
        pass
    return probes, submission


class AgentContext:
    """The harness capability the task-agent program orchestrates. The program calls run_agent to
    deploy probe-only claude sessions over the world and reads back what they observed; it owns the
    final reconstruction (returned from Solver.run). The meta agent evolves how many agents are
    deployed, how the work is split, what each is told, and what Python does with the results."""

    def __init__(self, world: RegisterWorld, cfg: Config, log=print):
        self.world = world
        self.cfg = cfg
        self.log = log
        self._used = 0
        self._obs: dict = {}          # idx -> color, accumulated across every agent spawned
        self.agent_calls: List[dict] = []  # audit trail for the sanitized report

    # ---- public world structure + state the program reads ----
    def world_map(self) -> dict:
        cells = [{"index": i, "coeffs": list(co), "const": k,
                  "formula": _cell_formula(co, k, self.world.spec.K)}
                 for i, (co, k) in enumerate(self.world.spec.cells())]
        return {"M": self.world.spec.M, "K": self.world.spec.K, "R": self.world.spec.R,
                "budget": self.world.spec.budget, "cells": cells}

    def remaining(self) -> int:
        return max(0, self.world.spec.budget - self._used)

    def observations(self) -> dict:
        return dict(self._obs)

    # ---- the one primitive: deploy a probe-only agent over the world ----
    def run_agent(self, prompt: str, *, max_probes: int = None, max_turns: int = None,
                  extra_tools=()) -> dict:
        """Spawn ONE airgapped claude session that can probe up to `max_probes` of the *global*
        remaining budget (default: all of it) and optionally submit a reconstruction. Returns
        {submission, observations (all accumulated so far), probes_used, result}."""
        rem = self.remaining()
        sub = rem if max_probes is None else max(0, min(int(max_probes), rem))
        if sub <= 0:
            return {"submission": None, "observations": self.observations(),
                    "probes_used": 0, "result": "no budget remaining"}
        if self.cfg.backend == "mock":
            return self._mock_agent(sub)
        traj = os.path.join(tempfile.gettempdir(), f"hta_agent_{uuid.uuid4().hex}.jsonl")
        open(traj, "w").close()
        server_env = {
            "HTA_TAPE": json.dumps(list(self.world.cells)),
            "HTA_BUDGET": str(sub),
            "HTA_TRAJ_PATH": traj,
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "PYTHONPATH": _REPO_ROOT + os.pathsep + os.environ.get("PYTHONPATH", ""),
        }
        argv = [sys.executable, "-m", "hta.ch2.probe_server"]
        res = llm.episode(prompt, model=self.cfg.task_model, mcp_server_argv=argv,
                          server_env=server_env, cwd=_REPO_ROOT,
                          allowed_tools=_ALLOWED_TOOLS + tuple(extra_tools),
                          max_turns=max_turns or sub * 3 + 12, role="ch2_agent", cfg=self.cfg)
        if res.get("is_error"):
            self.log(f"    agent error: {str(res.get('result'))[:120]}")
        probes, submission = _parse_agent_traj(traj)
        try:
            os.remove(traj)
        except OSError:
            pass
        return self._record(probes, submission, res.get("result"))

    def _mock_agent(self, sub: int) -> dict:
        """Deterministic stand-in (free): probe the next `sub` un-probed cells, do not submit.
        Lets the offline loop exercise the harness/scorer without a model."""
        nxt = [i for i in range(self.world.spec.M) if i not in self._obs][:sub]
        probes = [(i, int(self.world.cells[i]), True) for i in nxt]
        return self._record(probes, None, "mock")

    def _record(self, probes, submission, result) -> dict:
        charged, obs = 0, {}
        for idx, val, chg in probes:
            if chg:
                charged += 1
            if val is not None and isinstance(idx, int) and not isinstance(idx, bool):
                obs[idx] = val
        self._used += charged
        self._obs.update(obs)
        self.agent_calls.append({"probes_used": charged, "probed": sorted(obs),
                                 "submitted": submission is not None})
        return {"submission": submission, "observations": dict(self._obs),
                "probes_used": charged, "result": result}
