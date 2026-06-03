"""World-smith: the Opus curriculum generator.

It builds *training* worlds (whose difficulty it grows toward the agent's zone of
proximal development, and which it biases toward situations where research taste --
falsification, edge-case probing -- is what makes the difference) and exposes a
FROZEN *transfer* suite that it does not adapt, so generalization can be measured
fairly.

Generated rules are validated through the same strict AST whitelist as everything
else (hta.world.grammar) before they are ever compiled, so model output cannot
execute arbitrary code.
"""

import json
from typing import List, Optional

from .. import llm
from ..config import Config
from .grammar import RuleSpec, candidate_library, validate_lambda
from .engine import WiltWorld

_SMITH_PROMPT = """You are the WORLD-SMITH for an inductive-reasoning curriculum.
Invent hidden boolean rules over three numbers (x, y, z) for a Wason 2-4-6 style
task. Each rule is a Python lambda returning a bool, using only x, y, z, numeric
literals, comparisons, and/or/not, + - * / % ** //, and abs/min/max.

Design rules so that *research taste* is what separates good from bad solvers:
prefer rules where naive "confirm my guess" probing fails but falsifying, edge-case
probing (boundaries like <= vs <, rare exceptions, sign/zero cases) succeeds.
Target difficulty around {target_difficulty}/5 (1=easy, 5=hard). Escalate from what
the agent already handles.

Frontier (what the current best agent is weak at): {frontier}

Return ONLY JSON:
{{"rules": [{{"name": "...", "source": "lambda x, y, z: ...", "difficulty": N,
             "tags": ["falsification", "edge_cases", ...]}}, ...]}}
Return exactly {n} rules.

<<CTX>>{ctx}<<CTX>>"""

# Frozen held-out transfer worlds (never adapted) -> measures generalization.
_TRANSFER_NAMES = ["all_equal", "sum_eq", "all_positive", "y_is_avg",
                   "range_le_10", "two_equal"]


def _rulespecs_from_json(text: str) -> List[RuleSpec]:
    obj = llm.extract_json(text) or {}
    out = []
    for r in obj.get("rules", []):
        src = r.get("source", "")
        if validate_lambda(src):
            out.append(RuleSpec(r.get("name", "rule"), src,
                                r.get("difficulty", 3), tuple(r.get("tags", ()))))
    return out


def build_worlds(cfg: Config, target_difficulty: int = 2,
                 frontier: Optional[str] = None, log=print) -> List[WiltWorld]:
    n = cfg.n_train_worlds
    ctx = json.dumps({"role": "world_smith", "n": n,
                      "target_difficulty": target_difficulty})
    prompt = _SMITH_PROMPT.format(target_difficulty=target_difficulty,
                                  frontier=frontier or "(none yet)", n=n, ctx=ctx)
    try:
        text = llm.complete(prompt, model=cfg.world_model, role="world_smith", cfg=cfg)
        rules = _rulespecs_from_json(text)
    except Exception as e:
        log(f"  world-smith fell back to library: {e}")
        rules = []
    # backfill from the library if the smith returned too few valid rules
    if len(rules) < n:
        lib = candidate_library()
        lib.sort(key=lambda r: abs(r.difficulty - target_difficulty))
        for r in lib:
            if r.source not in {x.source for x in rules}:
                rules.append(r)
            if len(rules) >= n:
                break
    rules = rules[:n]
    log(f"  world-smith built {len(rules)} training worlds "
        f"(target_difficulty={target_difficulty})")
    return [WiltWorld(r, max_probes=cfg.max_probes) for r in rules]


def transfer_suite(cfg: Config) -> List[WiltWorld]:
    lib = {r.name: r for r in candidate_library()}
    chosen = [lib[name] for name in _TRANSFER_NAMES if name in lib][:cfg.n_transfer_worlds]
    return [WiltWorld(r, max_probes=cfg.max_probes) for r in chosen]
