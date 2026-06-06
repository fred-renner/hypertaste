"""TASTE plane: turn a probing trajectory + guess into research-taste metrics and a
single composite fitness. This is where "what good research behavior is" is defined.

We deliberately prefer *objective, computable* signals (exact recovery, agreement,
hypothesis-space reduction, novelty, simplicity) over an LLM judge, because the
agent is optimized against this number and an LLM judge would be gameable.
"""

import ast
from typing import List, Optional

from .config import Config


def _guess_complexity(src: Optional[str]) -> int:
    if not src:
        return 999
    try:
        tree = ast.parse(src, mode="eval")
    except Exception:
        return 999
    return sum(1 for _ in ast.walk(tree))


def occam_score(src: Optional[str]) -> float:
    """1.0 for a very simple guess, decaying with AST size. 0 if no valid guess. NOTE:
    this is now REPORT EVIDENCE only (a behavioral signal the meta agent may read), not a
    term in fitness -- the simplicity prior lives on the agent program via MDL selection,
    not on the per-world answer (see fitness() and program_description_length())."""
    size = _guess_complexity(src)
    if size >= 999:
        return 0.0
    # a bare "lambda x,y,z: x<y<z" is ~12 nodes; scale gently above that.
    return 1.0 / (1.0 + max(0, size - 12) / 12.0)


def program_description_length(source: str) -> Optional[int]:
    """A dumb, robust description-length proxy for the agent PROGRAM -- the Solomonoff/MDL
    prior, measured so it stays ungameable. It counts AST nodes + the character length of
    string/constant literals (so logic hidden in a long prompt string is not free), and
    ignores comments and whitespace (you can't pad your way shorter, or pay for blank
    lines). Returns None if the source doesn't parse -- an invalid program is not selected
    anyway. This is the only place 'Occam' enters the system, and it enters as a prior on
    the *program*, never as a term in the score the agent is optimized against."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    size = 0
    for node in ast.walk(tree):
        size += 1
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            size += len(node.value)
    return size


def compute_metrics(history: List[dict], guess: Optional[str], score: dict, hyp: dict) -> dict:
    used = len(history)
    real = [h for h in history if not h.get("malformed")]
    unique = len({tuple(h["triple"]) for h in real if h.get("triple")})
    reuse = (len(real) - unique) / len(real) if real else 0.0
    novelty = 1.0 - reuse
    malformed = sum(1 for h in history if h.get("malformed"))
    # falsification: fraction of probes that returned False (sought disconfirmation)
    false_frac = sum(1 for h in real if not h.get("label")) / len(real) if real else 0.0
    return {
        "solved": bool(score.get("solved")),
        "agreement": float(score.get("agreement", 0.0)),
        "valid_guess": bool(score.get("valid")),
        "probes_used": used,
        "unique_probes": unique,
        "novelty": round(novelty, 4),
        "reuse_rate": round(reuse, 4),
        "malformed": malformed,
        "false_frac": round(false_frac, 4),
        "avg_info_gain": round(float(hyp.get("avg_info_gain", 0.0)), 4),
        "hyp_reduced_frac": round(float(hyp.get("reduced_frac", 0.0)), 4),
        "occam": round(occam_score(guess), 4),
        "guess": guess,
    }


def fitness(metrics: dict, cfg: Config) -> float:
    """OUTCOME-only score. The agent is optimized against this number, so it must contain
    no taste prior: did it recover the rule (w_solve) and how close is the guess's behavior
    (w_approx). The taste/simplicity terms that used to be blended in here -- info-gain,
    novelty, occam -- are GONE; blending behaviors into the judge is Goodhart. They survive
    as EVIDENCE in the report (compute_metrics) for the meta agent to diagnose from, and the
    simplicity prior now lives where it belongs: a Solomonoff/MDL regularizer on the agent
    PROGRAM at selection time (program_description_length + Archive selection)."""
    f = (cfg.w_solve * (1.0 if metrics["solved"] else 0.0)
         + cfg.w_approx * metrics["agreement"])
    return round(f, 4)
