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
from typing import Callable, List, Tuple

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
# tags mark which research-taste behavior a rule rewards.
# ---------------------------------------------------------------------------
_RAW_CANDIDATES: List[Tuple[str, str, int, Tuple[str, ...]]] = [
    # name, source, difficulty, taste_tags
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
    ("inc_not_const", "lambda x, y, z: x < y < z and not (z - x == 4)", 5, ("ordering", "edge_cases", "falsification")),
    ("sum_lt_z2", "lambda x, y, z: x + y < z", 2, ("arithmetic",)),
    ("monotone", "lambda x, y, z: (x <= y <= z) or (x >= y >= z)", 3, ("ordering", "boundary")),
    ("first_smallest_last_largest", "lambda x, y, z: x < z and x <= y and y <= z", 4, ("ordering", "boundary")),
]


class RuleSpec:
    __slots__ = ("name", "source", "difficulty", "tags", "_fn")

    def __init__(self, name: str, source: str, difficulty: int, tags):
        self.name = name
        self.source = source
        self.difficulty = int(difficulty)
        self.tags = tuple(tags)
        self._fn = None

    @property
    def fn(self) -> Callable:
        if self._fn is None:
            self._fn = compile_rule(self.source)
        return self._fn

    def evaluate(self, triple) -> bool:
        return self.fn(*triple)

    def to_dict(self):
        return {"name": self.name, "source": self.source,
                "difficulty": self.difficulty, "tags": list(self.tags)}

    @staticmethod
    def from_dict(d) -> "RuleSpec":
        return RuleSpec(d["name"], d["source"], d.get("difficulty", 3), d.get("tags", ()))

    def __repr__(self):
        return f"RuleSpec({self.name!r}, diff={self.difficulty})"


def candidate_library() -> List[RuleSpec]:
    return [RuleSpec(n, s, d, t) for (n, s, d, t) in _RAW_CANDIDATES]


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
