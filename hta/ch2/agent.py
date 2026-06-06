"""The student plane for the slice: the two episode prompts we are A/B-ing (vanilla vs a
hand-written taste prompt), a deterministic mock solver for free plumbing tests, and the
real single-session runner (reusing hta.llm.episode + the Chapter-2 probe server).

Fairness note: BOTH prompts describe the world identically (size, alphabet, the family, and
that the tape splits into contiguous segments). NEITHER is told how many segments there are
or where the boundaries fall — segmentation must be inferred. The only difference is research
*taste* — the taste prompt adds the investigative strategy (infer the boundaries; read each
region with the fewest probes that resolve it; spend the costly confirm-probe ONLY on the
genuinely ambiguous arith/cycle mirage; allocate to the long runs first). It names no
boundary, count, or value, so the gap it produces is a taste gap, not an information
advantage. The strategy is budget-aware by design: a blanket spread-and-confirm overspends a
scarce budget, so the discipline is to pay for certainty only where it is actually in doubt.
"""

import json
import os
import sys
import tempfile
import uuid
from typing import List, Optional

from .. import llm
from ..config import Config
from . import grammar
from .grammar import TapeSpec
from .world import TapeWorld

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ALLOWED_TOOLS = ("mcp__probe__probe", "mcp__probe__remaining", "mcp__probe__submit_map")


_COMMON = """\
You are reconstructing a hidden tape of {M} cells, indexed 0..{M_1}. Each cell holds an
integer color in 0..{K_1}. The tape is divided into some number of consecutive segments;
within each segment the colors follow ONE simple pattern from this family:
  - const:  every cell the same value v
  - arith:  v, v+s, v+2s, ... (mod {K}); a hidden start v and step s
  - alt:    v, w, v, w, ... ; two alternating values
  - cycle:  a, b, c, a, b, c, ... ; three values repeating with period 3
You are NOT told how many segments there are or where the boundaries fall — you must infer
the segmentation from what you probe.

You have {budget} probes total. Tools:
  - probe(index): reveal one cell's color; returns the value and probes remaining.
  - submit_map(values): submit a JSON array of {M} integers (one per cell, in order). Ends
    the episode. You MUST call this exactly once before finishing.
Act through tools only; emit no prose between tool calls.
"""

VANILLA = _COMMON + """\
Probe cells and then submit your best reconstruction of all {M} cells.
"""

TASTE = _COMMON + """\
Strategy (research taste) — your budget is far too small to probe every cell, so spend each
probe where it buys the most, and do NOT pay for certainty you already have:
1. Map before you mine. Probe a SPREAD of cells across the whole tape first to find where the
   pattern changes; don't cluster probes in one place. A boundary is where a neighbouring cell
   stops fitting the pattern you were reading.
2. Resolve each region with the FEWEST probes that settle it. Many runs declare themselves in
   two or three adjacent cells (a flat run is const; a clean v,w,v,w is alt) — once a run is
   obviously uniform or obviously alternating, bank its whole extent and move ON; do not spend
   another probe confirming what is already clear.
3. Spend the costly confirm-probe ONLY on the real ambiguity. Three rising cells [a, a+s, a+2s]
   are the opening of an arith run AND of a period-3 cycle that snaps back at the next cell — a
   local read cannot tell them apart, and guessing wrong forfeits the whole run. THERE, and
   only there, spend ONE probe further along (the very next cell, or a far cell the pattern
   predicts): if it keeps stepping it is arith, if it falls back to the start it is cycle. One
   probe buys the rest of the segment.
4. Allocate like a knapsack: a long run pinned is worth many cells per probe, a short one few —
   so find and bank the LONG runs first, and do not pour scarce probes into short, flashy,
   high-variation stretches.
5. Fill in every cell by continuing the pattern you inferred; for any region you could not
   pin down, put your single best guess. Submit a complete {M}-cell reconstruction — never
   leave a cell out.
"""


def build_prompt(spec: TapeSpec, taste: bool) -> str:
    tmpl = TASTE if taste else VANILLA
    return tmpl.format(M=spec.M, M_1=spec.M - 1, K_1=spec.K - 1, K=spec.K,
                       budget=spec.budget)


# ---------------------------------------------------------------------------
# Deterministic mock solver (free): proves the world admits a high-coverage strategy and
# exercises the scorer. NOT a claim about Haiku — that is the live measurement below.
# ---------------------------------------------------------------------------
def _infer_segment(n: int, K: int, idxs, vals) -> List[int]:
    """Best full-segment prediction from local observations: determined cells exact, the
    rest filled from the first consistent family candidate (deterministic)."""
    cands = grammar.seg_candidates(n, K)
    consistent = [s for s in cands if all(s[i] == v for i, v in zip(idxs, vals))]
    if not consistent:
        return [vals[0] if vals else 0] * n
    out = []
    for j in range(n):
        col = {s[j] for s in consistent}
        out.append(next(iter(col)) if len(col) == 1 else consistent[0][j])
    return out


def mock_solve(spec: TapeSpec, taste: bool) -> List[int]:
    world = TapeWorld(spec)
    ch = world.open_channel()
    bounds = spec.bounds()
    recon = [0] * spec.M
    if not taste:
        # vanilla: probe the first `budget` cells, guess 0 elsewhere (no inference).
        for i in range(min(spec.budget, spec.M)):
            recon[i] = ch.probe(i)
        return recon
    # taste: allocate probes longest-first; probe a few CONSECUTIVE cells per segment, then
    # extrapolate. Four consecutive colors break every short-window ambiguity in the family
    # (const/arith/alt, and the arith-vs-cycle mirage that a 3-cell read cannot resolve).
    # knapsack-greedy under scarcity: fully pin the LONGEST segments first; a half-probed
    # segment is worth little, so spend to pin the high-yield ones and guess the rest. This
    # is the value-of-information allocation the oracle also makes. (mock cheats with the
    # known bounds; it is a plumbing/scorer check, NOT a claim about Haiku.)
    order = sorted(range(len(bounds)), key=lambda j: -(bounds[j][1] - bounds[j][0]))
    plan = {j: [] for j in range(len(bounds))}
    budget = spec.budget
    for j in order:
        n = bounds[j][1] - bounds[j][0]
        for p in range(min(4, n)):
            if budget <= 0:
                break
            plan[j].append(p)
            budget -= 1
    for j, (a, b) in enumerate(bounds):
        n = b - a
        idxs, vals = [], []
        for p in plan[j]:
            v = ch.probe(a + p)
            if v is not None:
                idxs.append(p)
                vals.append(v)
        seg = _infer_segment(n, spec.K, idxs, vals) if idxs else [0] * n
        recon[a:b] = seg
    return recon


# ---------------------------------------------------------------------------
# Real single-session episode (one claude -p session, probe channel as a stdio-MCP tool).
# ---------------------------------------------------------------------------
def real_solve(spec: TapeSpec, taste: bool, cfg: Config, log=print) -> List[int]:
    traj = os.path.join(tempfile.gettempdir(), f"hta_ch2_{uuid.uuid4().hex}.jsonl")
    open(traj, "w").close()
    tape = grammar.expand(spec)
    server_env = {
        "HTA_TAPE": json.dumps(list(tape)),
        "HTA_BUDGET": str(spec.budget),
        "HTA_TRAJ_PATH": traj,
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONPATH": _REPO_ROOT + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    argv = [sys.executable, "-m", "hta.ch2.probe_server"]
    prompt = build_prompt(spec, taste)
    res = llm.episode(prompt, model=cfg.task_model, mcp_server_argv=argv,
                      server_env=server_env, cwd=_REPO_ROOT, allowed_tools=_ALLOWED_TOOLS,
                      max_turns=spec.budget * 2 + cfg.episode_turn_buffer,
                      role="ch2_episode", cfg=cfg)
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


def solve(spec: TapeSpec, taste: bool, cfg: Config, log=print) -> List[int]:
    """Dispatch: mock backend uses the deterministic solver; real backend runs a live
    single-session Haiku episode."""
    if cfg.backend == "mock":
        return mock_solve(spec, taste)
    return real_solve(spec, taste, cfg, log=log)
