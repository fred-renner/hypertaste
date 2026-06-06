"""The student plane for the slice: the two episode prompts we are A/B-ing (vanilla vs a
hand-written taste prompt), a deterministic mock solver for free plumbing tests, and the
real single-session runner (reusing hta.llm.episode + the Chapter-2 probe server).

Fairness note: BOTH prompts describe the world identically (size, alphabet, the family, and
that the tape splits into contiguous segments). NEITHER is told how many segments there are
or where the boundaries fall — segmentation must be inferred. The only difference is research
*taste*, and it is deliberately GENERAL: a transferable investigative disposition (infer the
structure and predict the unseen; seek disconfirming evidence; spend observations where
uncertainty is highest; revise when something doesn't fit). It names no task-specific tactic —
no boundary, count, value, family member, or "confirm-trick". An earlier version spelled out
the exact arith/cycle confirm move; that was wrong on two counts — it is not a fight worth
winning by telling the model the answer, and a tactic tied to this puzzle cannot transfer,
which is the whole point of the artifact. Taste here must be a disposition the loop could grow
and carry to other worlds, never a cheat-sheet for one.
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
Approach this the way a careful researcher works under a tight budget — a general disposition,
not a recipe for this particular puzzle:
- You cannot observe everything, so your real job is to INFER the underlying structure from a
  few observations and then predict the rest, not merely report what you saw.
- Form a hypothesis about what generates the data, then actively try to DISPROVE it. An
  observation that could contradict your current guess is worth more than one that merely
  agrees with it; don't trust a first impression you haven't tested.
- Spend each observation where your uncertainty is greatest and where one reading tells you the
  most about the cells you can't afford to check.
- When something doesn't fit, revise rather than force it; consolidate what you've learned
  before you commit.
Then submit your best inference for EVERY cell — a complete {M}-cell reconstruction, never
leaving one out.
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
    # max_turns is generous on purpose. At budget*2+6 a chatty Haiku could exhaust its turns
    # before submitting (one episode hit error_max_turns and scored ~0, corrupting the gap),
    # so we give 3 turns/probe + headroom. A well-behaved episode submits early and never
    # touches this; only a runaway costs the extra turns, so the binding constraint stays the
    # PROBE budget, never the turn cap.
    res = llm.episode(prompt, model=cfg.task_model, mcp_server_argv=argv,
                      server_env=server_env, cwd=_REPO_ROOT, allowed_tools=_ALLOWED_TOOLS,
                      max_turns=spec.budget * 3 + 12,
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
