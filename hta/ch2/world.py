"""TapeWorld: one hidden tape + the objective coverage judge (the integrity floor).

The world owns the hidden tape. It hands the agent a MapChannel (one cell value per
probe) and, after the agent submits a full reconstruction, scores it by **coverage** —
the fraction of cells it got right — normalized between a no-inference floor and the
model-free DP oracle on the same world and budget.

Scoring lives here, in the world plane, never in the agent's reach. The score is the
value the agent ACTUALLY uncovered (its reconstruction vs the truth), not its proximity
to the oracle's probe path — discovery is scored as an outcome, never as imitation.
"""

from typing import List, Optional

from . import grammar
from .grammar import TapeSpec


class ProbeExhausted(Exception):
    pass


class MapChannel:
    """The ONLY interface between the agent and a tape. probe(index) -> one cell color and
    nothing else; the tape, the grammar, and the scorer are not reachable from here. The
    Chapter-2 analogue of Chapter-1's boolean ProbeChannel — a richer payload (a color, not
    a bit) but the same narrow, append-only anti-leak wall."""

    def __init__(self, tape, max_probes: int):
        self._tape = tuple(tape)
        self._max = int(max_probes)
        self._history: List[dict] = []

    def remaining(self) -> int:
        return self._max - len(self._history)

    def probe(self, index) -> Optional[int]:
        if self.remaining() <= 0:
            raise ProbeExhausted("no probes remaining")
        if not isinstance(index, int) or isinstance(index, bool) or not (0 <= index < len(self._tape)):
            self._history.append({"index": None, "value": None, "malformed": True})
            return None
        val = self._tape[index]
        self._history.append({"index": index, "value": val, "malformed": False})
        return val

    def history(self) -> List[dict]:
        return list(self._history)

    def used(self) -> int:
        return len(self._history)


class TapeWorld:
    def __init__(self, spec: TapeSpec, budget: Optional[int] = None):
        self.spec = spec
        self.budget = spec.budget if budget is None else budget
        self.tape = grammar.expand(spec)

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def M(self) -> int:
        return self.spec.M

    def open_channel(self) -> MapChannel:
        return MapChannel(self.tape, self.budget)

    # ---- references (world plane; model-free, agent-inaccessible) ----
    def references(self) -> dict:
        """The bracket the student is measured against: a no-inference floor, a *realizable*
        ceiling (the normalizer — the oracle de-omnisciented by charging it for boundary
        discovery), and the omniscient DP oracle (kept for reporting/diagnostics). All as raw
        correct/M coverage (determined cells for sure + 1/K luck on the rest)."""
        K, M = self.spec.K, self.M
        det_oracle = grammar.oracle_determined(self.spec, self.budget)
        det_floor = grammar.floor_determined(self.spec, self.budget)
        det_real = grammar.realizable_determined(self.spec, self.budget)
        return {
            "oracle_det": det_oracle,
            "floor_det": det_floor,
            "realizable_det": det_real,
            "oracle_raw": self._raw_from_determined(det_oracle, K, M),
            "floor_raw": self._raw_from_determined(det_floor, K, M),
            "realizable_raw": self._raw_from_determined(det_real, K, M),
        }

    @staticmethod
    def _raw_from_determined(det: int, K: int, M: int) -> float:
        """Raw coverage of a player that nails `det` cells and guesses the rest (1/K)."""
        return det / M + (1.0 / K) * (1 - det / M)

    # ---- scoring (world plane) ----
    def score(self, reconstruction: Optional[List[int]]) -> dict:
        """Score a submitted full-tape reconstruction. raw = fraction of cells correct;
        normalized = where raw sits between the floor and the *realizable* ceiling (clamped
        [0,1]). The omniscient oracle was too tall a denominator and compressed everyone near
        zero, so we normalize against what a boundary-discovering player can actually reach."""
        M = self.M
        recon = reconstruction or []
        correct = sum(1 for i in range(M)
                      if i < len(recon) and recon[i] == self.tape[i])
        raw = correct / M
        ref = self.references()
        denom = ref["realizable_raw"] - ref["floor_raw"]
        norm = 0.0 if denom <= 0 else (raw - ref["floor_raw"]) / denom
        return {
            "raw": round(raw, 4),
            "normalized": round(max(0.0, min(1.0, norm)), 4),
            "correct": correct,
            "M": M,
            "valid": bool(reconstruction) and len(recon) == M,
        }
