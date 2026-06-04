"""WILT rule grammar: safe compilation + a candidate hypothesis library.

The candidate library is the *hypothesis space* (a legitimate prior, like a human
knowing "the rule is some simple boolean function of three numbers"). It is used:
  * by the TASTE plane to measure hypothesis-space reduction (info gain), and
  * by the offline mock inductor to do Occam induction from observed probes.

It is NOT the hidden rule. The hidden rule is held in hta.world.engine and is
never exposed.

Safety: any lambda we compile (candidate, world-smith output, or an agent's final
guess) is AST-validated against a strict whitelist and evaluated with no builtins.
This prevents arbitrary code execution from model-generated strings.
"""

import ast
import random
from typing import Callable, List, Optional, Tuple

# Functions an expression may call.
ALLOWED_FUNCS = {"abs": abs, "min": min, "max": max}

_ALLOWED_NODES = (
    ast.Expression, ast.Lambda, ast.arguments, ast.arg,
    ast.Compare, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.IfExp,
    ast.Name, ast.Load, ast.Constant, ast.Call,
    ast.And, ast.Or, ast.Not, ast.USub, ast.UAdd,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv,
)


def validate_lambda(src: str) -> bool:
    """True iff `src` is a single lambda over <=3 numeric args using only the
    whitelisted operators/functions and the arg names + ALLOWED_FUNCS."""
    src = (src or "").strip()
    try:
        tree = ast.parse(src, mode="eval")
    except (SyntaxError, ValueError):
        return False
    if not isinstance(tree.body, ast.Lambda):
        return False
    lam = tree.body
    if lam.args.vararg or lam.args.kwarg or lam.args.kwonlyargs or lam.args.defaults:
        return False
    arg_names = [a.arg for a in lam.args.args]
    if not (1 <= len(arg_names) <= 3):
        return False
    allowed_names = set(arg_names) | set(ALLOWED_FUNCS)
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            return False
        if isinstance(node, ast.Name) and node.id not in allowed_names:
            return False
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float, bool)):
            return False
        if isinstance(node, ast.Call):
            if not (isinstance(node.func, ast.Name) and node.func.id in ALLOWED_FUNCS):
                return False
            if node.keywords:
                return False
    return True


def compile_rule(src: str) -> Callable:
    """Compile a validated lambda string into a callable f(x, y, z) -> bool-ish.
    Raises ValueError if the string is unsafe or invalid."""
    if not validate_lambda(src):
        raise ValueError(f"unsafe or invalid rule: {src!r}")
    code = compile(ast.parse(src.strip(), mode="eval"), "<rule>", "eval")
    fn = eval(code, {"__builtins__": {}}, dict(ALLOWED_FUNCS))  # noqa: S307 (sandboxed)

    def safe(x, y, z):
        try:
            return bool(fn(x, y, z))
        except Exception:
            return False

    return safe


# ---------------------------------------------------------------------------
# Candidate hypothesis library (ordered roughly easy -> hard).
# tags mark which research-taste behavior a rule rewards; `structure` marks the
# compositional shape (atomic | conjunction | regime | exception) -- the axis the
# world-smith climbs (WORLD_DESIGN.md Axis A). Entries are 4-tuples (atomic, the
# default) or 5-tuples that name an explicit structure.
# ---------------------------------------------------------------------------
STRUCTURES = ("atomic", "conjunction", "regime", "exception")

_RAW_CANDIDATES: List[Tuple] = [
    # name, source, difficulty, taste_tags[, structure]
    ("strict_increasing", "lambda x, y, z: x < y < z", 1, ("ordering",)),
    ("non_decreasing", "lambda x, y, z: x <= y <= z", 2, ("boundary", "edge_cases")),
    ("strict_decreasing", "lambda x, y, z: x > y > z", 1, ("ordering",)),
    ("all_equal", "lambda x, y, z: x == y == z", 1, ("equality",)),
    ("any_order_distinct", "lambda x, y, z: x != y and y != z and x != z", 2, ("equality",)),
    ("sum_eq", "lambda x, y, z: x + y == z", 2, ("arithmetic",)),
    ("sum_pos", "lambda x, y, z: x + y + z > 0", 2, ("sign", "arithmetic")),
    ("product_pos", "lambda x, y, z: x * y * z > 0", 3, ("sign",)),
    ("arithmetic_prog", "lambda x, y, z: y - x == z - y", 3, ("arithmetic", "edge_cases")),
    ("constant_gap2", "lambda x, y, z: y == x + 2 and z == y + 2", 3, ("arithmetic",)),
    ("all_positive", "lambda x, y, z: x > 0 and y > 0 and z > 0", 1, ("sign",)),
    ("all_even", "lambda x, y, z: x % 2 == 0 and y % 2 == 0 and z % 2 == 0", 3, ("parity",)),
    ("increasing_even_gap", "lambda x, y, z: x < y < z and (z - x) % 2 == 0", 4, ("ordering", "parity", "edge_cases")),
    ("max_is_z", "lambda x, y, z: z >= x and z >= y", 2, ("ordering", "boundary")),
    ("min_is_x", "lambda x, y, z: x <= y and x <= z", 2, ("ordering", "boundary")),
    ("range_le_10", "lambda x, y, z: max(x, y, z) - min(x, y, z) <= 10", 3, ("arithmetic", "edge_cases")),
    ("contains_zero", "lambda x, y, z: x == 0 or y == 0 or z == 0", 2, ("edge_cases",)),
    ("strictly_inc_pos", "lambda x, y, z: 0 < x < y < z", 3, ("ordering", "sign", "edge_cases")),
    ("y_is_avg", "lambda x, y, z: x + z == 2 * y", 3, ("arithmetic",)),
    ("abs_sum_eq", "lambda x, y, z: abs(x) + abs(y) == abs(z)", 4, ("arithmetic", "sign")),
    ("two_equal", "lambda x, y, z: x == y or y == z or x == z", 2, ("equality", "edge_cases")),
    ("inc_not_const", "lambda x, y, z: x < y < z and not (z - x == 4)", 5, ("ordering", "edge_cases", "falsification"), "exception"),
    ("sum_lt_z2", "lambda x, y, z: x + y < z", 2, ("arithmetic",)),
    ("monotone", "lambda x, y, z: (x <= y <= z) or (x >= y >= z)", 3, ("ordering", "boundary"), "conjunction"),
    ("first_smallest_last_largest", "lambda x, y, z: x < z and x <= y and y <= z", 4, ("ordering", "boundary"), "conjunction"),
    # ---- compositional seeds (Axis A): regimes, conjunctions, exceptions. The
    # grammar already admits and/or/not + ternaries, so these are safe to compile
    # today; they are where research taste (hypothesis decomposition, falsification)
    # pays off, and they let the offline Occam inductor cover the harder curriculum.
    ("regime_sign_order", "lambda x, y, z: (x < y < z) if x < 0 else (x > y > z)", 4, ("ordering", "sign", "edge_cases"), "regime"),
    ("regime_sum_sign", "lambda x, y, z: (x + y + z > 0) if z >= 0 else (x + y + z < 0)", 4, ("sign", "arithmetic", "boundary"), "regime"),
    ("inc_and_sum_pos", "lambda x, y, z: x < y < z and x + y + z > 0", 3, ("ordering", "sign", "arithmetic"), "conjunction"),
    ("strict_inc_or_dec", "lambda x, y, z: (x < y < z) or (x > y > z)", 3, ("ordering",), "conjunction"),
    ("inc_mid_nonzero", "lambda x, y, z: x < y < z and not (y == 0)", 4, ("ordering", "sign", "falsification"), "exception"),
    ("nondec_not_const", "lambda x, y, z: x <= y <= z and not (x == y == z)", 4, ("ordering", "equality", "edge_cases", "falsification"), "exception"),
    ("sum_eq_and_ordered", "lambda x, y, z: x + y == z and x < y", 4, ("arithmetic", "ordering"), "conjunction"),
]


class RuleSpec:
    __slots__ = ("name", "source", "difficulty", "tags", "structure", "_fn")

    def __init__(self, name: str, source: str, difficulty: int, tags, structure: str = "atomic"):
        self.name = name
        self.source = source
        self.difficulty = int(difficulty)
        self.tags = tuple(tags)
        self.structure = structure if structure in STRUCTURES else "atomic"
        self._fn = None

    @property
    def fn(self) -> Callable:
        if self._fn is None:
            self._fn = compile_rule(self.source)
        return self._fn

    def evaluate(self, triple) -> bool:
        return self.fn(*triple)

    def to_dict(self):
        return {"name": self.name, "source": self.source, "difficulty": self.difficulty,
                "tags": list(self.tags), "structure": self.structure}

    @staticmethod
    def from_dict(d) -> "RuleSpec":
        return RuleSpec(d["name"], d["source"], d.get("difficulty", 3),
                        d.get("tags", ()), d.get("structure", "atomic"))

    def __repr__(self):
        return f"RuleSpec({self.name!r}, diff={self.difficulty}, structure={self.structure!r})"


def candidate_library() -> List[RuleSpec]:
    # entries are (name, source, difficulty, tags) or (..., structure); 4-tuples
    # default to atomic.
    out = []
    for e in _RAW_CANDIDATES:
        structure = e[4] if len(e) > 4 else "atomic"
        out.append(RuleSpec(e[0], e[1], e[2], e[3], structure))
    return out


def consistent_candidates(history, candidates=None) -> List[RuleSpec]:
    """Subset of the candidate library whose predictions match every observed
    (triple, label) pair. history items: {"triple": [...], "label": bool}."""
    if candidates is None:
        candidates = candidate_library()
    out = []
    for c in candidates:
        ok = True
        for h in history:
            if c.evaluate(h["triple"]) != bool(h["label"]):
                ok = False
                break
        if ok:
            out.append(c)
    return out


def simplest_consistent(history, candidates=None) -> RuleSpec:
    """Occam choice: the shortest-source candidate consistent with observations.
    Returns None if nothing is consistent. Uses ONLY observed booleans."""
    cands = consistent_candidates(history, candidates)
    if not cands:
        return None
    return min(cands, key=lambda c: (len(c.source), c.difficulty))


# ---------------------------------------------------------------------------
# Generative hypothesis space (WORLD_DESIGN.md Axis B).
#
# `hypothesis_reduction` (the info-gain metric) used to measure version-space
# collapse over the fixed 25-rule candidate library, which doubled as both the
# measurable hypothesis space AND the smith's fallback. The instant Axis A produces
# rules outside those templates the library no longer contains the true rule and the
# metric goes noisy. `sample_hypotheses` decouples them: it draws valid (AST-checked)
# rules straight from the grammar -- including compositional structures -- so the
# metric measures hypothesis-space collapse over a *sampled* version space, a pure
# function of the hidden rule + the probes. Every sampled rule is built from the same
# whitelist and re-validated, so it is safe by construction.
# ---------------------------------------------------------------------------
_PERMS = (("x", "y", "z"), ("x", "z", "y"), ("y", "x", "z"),
          ("y", "z", "x"), ("z", "x", "y"), ("z", "y", "x"))
_CMP = ("<", "<=", ">", ">=")
_STRUCT_WEIGHTS = {"atomic": 5, "conjunction": 3, "regime": 2, "exception": 2}


def _gen_atomic(rng: random.Random) -> str:
    kind = rng.choice(["chain", "pair", "sum_k", "two_sum", "avg", "parity",
                       "absrel", "gap", "range"])
    a, b, c = rng.choice(_PERMS)
    if kind == "chain":
        op = rng.choice(_CMP)
        return f"{a} {op} {b} {op} {c}"
    if kind == "pair":
        op = rng.choice(_CMP + ("==", "!="))
        return f"{a} {op} {b}"
    if kind == "sum_k":
        op = rng.choice(["==", ">", "<", ">=", "<="])
        return f"x + y + z {op} {rng.randint(-3, 3)}"
    if kind == "two_sum":
        op = rng.choice(["==", ">", "<", ">=", "<="])
        return f"{a} + {b} {op} {c}"
    if kind == "avg":
        op = rng.choice(["==", ">", "<"])
        return f"{a} + {c} {op} 2 * {b}"
    if kind == "parity":
        return f"({a} + {b}) % 2 == 0" if rng.random() < 0.5 else f"{a} % 2 == 0"
    if kind == "absrel":
        op = rng.choice(["==", ">", "<", ">=", "<="])
        return f"abs({a}) + abs({b}) {op} abs({c})"
    if kind == "gap":
        op = rng.choice(["==", ">", "<", ">=", "<="])
        return f"{b} - {a} {op} {rng.randint(-2, 4)}"
    # range
    op = rng.choice(["<=", ">=", "<", ">", "=="])
    return f"max(x, y, z) - min(x, y, z) {op} {rng.randint(1, 10)}"


def _build(rng: random.Random, structure: str) -> str:
    if structure == "atomic":
        return _gen_atomic(rng)
    if structure == "conjunction":
        op = rng.choice(["and", "or"])
        return f"({_gen_atomic(rng)}) {op} ({_gen_atomic(rng)})"
    if structure == "regime":
        return f"({_gen_atomic(rng)}) if ({_gen_atomic(rng)}) else ({_gen_atomic(rng)})"
    # exception
    return f"({_gen_atomic(rng)}) and not ({_gen_atomic(rng)})"


def _weighted_structure(rng: random.Random, allowed: Tuple[str, ...]) -> str:
    weights = [_STRUCT_WEIGHTS[s] for s in allowed]
    return rng.choices(allowed, weights=weights, k=1)[0]


_DIFF_FOR = {"atomic": 2, "conjunction": 3, "regime": 4, "exception": 4}


def sample_hypotheses(seed: int, k: int, max_structure: str = "exception",
                      include_library: bool = True) -> List[RuleSpec]:
    """Draw `k` valid rules from the grammar, deterministically per `seed`, biased
    toward the curriculum's structure mix and capped at `max_structure` complexity.
    With `include_library` the candidate library is prepended as a prior so the
    version space is always grounded. Every rule is re-validated, so the returned set
    is safe to compile."""
    if max_structure not in STRUCTURES:
        max_structure = "exception"
    allowed = STRUCTURES[:STRUCTURES.index(max_structure) + 1]
    rng = random.Random(seed)
    out: List[RuleSpec] = []
    seen = set()
    if include_library:
        for r in candidate_library():
            if r.source not in seen:
                seen.add(r.source)
                out.append(r)
    made, attempts = 0, 0
    while made < k and attempts < k * 50 + 100:
        attempts += 1
        structure = _weighted_structure(rng, allowed)
        body = f"lambda x, y, z: {_build(rng, structure)}"
        if body in seen or not validate_lambda(body):
            continue
        seen.add(body)
        out.append(RuleSpec(f"hyp_{seed & 0xffff}_{made}", body,
                            _DIFF_FOR[structure], ("sampled", structure), structure))
        made += 1
    return out
