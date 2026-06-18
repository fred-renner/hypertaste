"""Integrity-floor tests for the world-building substrate -- the invariants that survive every chapter.

- **Model-free by construction.** Nothing under `hta/lab/` (the grader) or `hta/world/` (the content)
  imports `hta.llm`. A module that cannot call a model cannot be gamed by one -- the dumb,
  deterministic, agent-inaccessible scorer the whole design rests on.
- **The smith proposes structure, never the score.** Every spec the smith emits carries only
  structural keys; it never writes a coverage, oracle, floor, or any judgement. The referee and the
  benchmark are re-derived mechanically from the structure -- an inventor that could also move the
  score would just mint worlds that *look* solved.
"""

import ast
import pathlib
import subprocess
import sys

from hta.gym import smith
from hta.world.seed import seed_spec

ROOT = pathlib.Path(__file__).resolve().parent.parent / "hta"


def _imports(py: pathlib.Path):
    """Every dotted module name imported by a source file (both `import x` and `from x import ...`)."""
    tree = ast.parse(py.read_text(), filename=str(py))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module


def test_no_llm_import_under_lab_and_world():
    for sub in ("lab", "world"):
        for py in (ROOT / sub).rglob("*.py"):
            for mod in _imports(py):
                assert not mod.startswith("hta.llm"), f"{py} imports the model layer ({mod})"


def test_grader_and_world_do_not_pull_in_llm_at_runtime():
    # Importing the grader + the world grammar + the seed must not TRANSITIVELY load hta.llm. Run in
    # a FRESH interpreter: in the shared pytest process the trail's tests have already imported the
    # model layer, so sys.modules there is contaminated -- a clean subprocess is the honest check.
    probe = ("import sys; import hta.lab.scoring, hta.world.spec, hta.world.seed; "
             "sys.exit(1 if 'hta.llm' in sys.modules else 0)")
    r = subprocess.run([sys.executable, "-c", probe], cwd=str(ROOT.parent))
    assert r.returncode == 0, "importing the grader/world transitively loaded hta.llm"


def test_smith_emits_specs_not_scores():
    # The smith's output is STRUCTURE as data: only the spec's structural keys, never a judgement.
    allowed = {"name", "n_vars", "K", "budget", "bait", "payoff", "cost_bait", "cost_gate"}
    forbidden = {"score", "oracle", "floor", "reachable", "fix", "champion", "ship", "hard", "gap"}
    for variant in smith.spread(seed_spec()):
        assert set(variant) <= allowed
        assert not (set(variant) & forbidden)
