"""MechWorld: one hidden mechanism + the objective coverage judge (the integrity floor).

The world owns the hidden forest. It hands the agent a MechChannel (poke a node -> its
reachable set, and nothing else) and, after the agent submits a reconstructed edge set,
scores it by **F1 of the wiring** -- normalized between the false-compass floor and the
realizable, structure-reading ceiling on the same world and budget.

Scoring lives here, in the world plane, never in the agent's reach. The score is the wiring
the agent ACTUALLY recovered (its edges vs the truth), not its proximity to any oracle path
-- discovery is scored as an outcome, never as imitation.
"""

from typing import List, Optional, Tuple

from . import graph
from .graph import MechSpec


class ProbeExhausted(Exception):
    pass


class MechChannel:
    """The ONLY interface between the agent and a mechanism. poke(node) -> the sorted list of
    that node's descendants (what it lights up) and nothing else; the wiring and the scorer are
    not reachable from here. The narrow, append-only anti-leak wall."""

    def __init__(self, reach, max_probes: int):
        self._reach = reach
        self._n = len(reach)
        self._max = int(max_probes)
        self._history: List[dict] = []

    def remaining(self) -> int:
        return self._max - len(self._history)

    def poke(self, node) -> Optional[List[int]]:
        if self.remaining() <= 0:
            raise ProbeExhausted("no probes remaining")
        if not isinstance(node, int) or isinstance(node, bool) or not (0 <= node < self._n):
            self._history.append({"node": None, "reach": None, "malformed": True})
            return None
        out = sorted(self._reach[node])
        self._history.append({"node": node, "reach": out, "malformed": False})
        return out

    def history(self) -> List[dict]:
        return list(self._history)

    def used(self) -> int:
        return len(self._history)


class MechWorld:
    def __init__(self, spec: MechSpec, budget: Optional[int] = None):
        self.spec = spec
        self.budget = spec.budget if budget is None else budget
        self.parent, self.edges, self.reach, self.module_of = graph.expand(spec)

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def N(self) -> int:
        return self.spec.N

    def open_channel(self) -> MechChannel:
        return MechChannel(self.reach, self.budget)

    # ---- references (world plane; model-free, agent-inaccessible) ----
    def references(self) -> dict:
        return graph.references(self.spec)

    # ---- scoring (world plane) ----
    def score(self, pred_edges: Optional[List]) -> dict:
        """Score a submitted edge set (list of [parent, child] pairs). raw = F1 against the
        true wiring; normalized = where raw sits between the false-compass floor and the
        realizable ceiling (clamped [0,1])."""
        pred = _clean_edges(pred_edges, self.N)
        raw, prec, rec = graph.f1(pred, self.edges)
        ref = self.references()
        denom = ref["realizable_f1"] - ref["floor_f1"]
        norm = 0.0 if denom <= 0 else (raw - ref["floor_f1"]) / denom
        return {
            "raw": round(raw, 4),
            "normalized": round(max(0.0, min(1.0, norm)), 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "n_pred": len(pred),
            "n_true": len(self.edges),
            "valid": pred_edges is not None,
        }


def _clean_edges(pred_edges: Optional[List], n: int) -> set:
    """Coerce a submitted edge list into a clean set of valid (parent, child) int pairs;
    drop anything malformed or out of range. Self-loops are dropped."""
    out = set()
    if not pred_edges:
        return out
    for e in pred_edges:
        if (isinstance(e, (list, tuple)) and len(e) == 2
                and all(isinstance(x, int) and not isinstance(x, bool) for x in e)
                and 0 <= e[0] < n and 0 <= e[1] < n and e[0] != e[1]):
            out.add((int(e[0]), int(e[1])))
    return out
