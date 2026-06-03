"""ProbeChannel: the ONLY interface between the task agent and a world.

The agent receives a ProbeChannel. It can submit a test case and learn one
boolean ("True/False, N attempts remaining") and nothing else. The hidden rule,
its source, and the scorer are not reachable from here. This narrow, append-only
channel is simultaneously the anti-leak wall and the scientific-validity wall:
research taste can only be expressed through probing.
"""

from typing import Callable, List, Optional


class ProbeExhausted(Exception):
    pass


def _valid_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class ProbeChannel:
    def __init__(self, hidden_fn: Callable, max_probes: int):
        self._hidden = hidden_fn
        self._max = int(max_probes)
        self._history: List[dict] = []
        self._seen = set()

    # ---- agent-facing API ----
    def remaining(self) -> int:
        return self._max - len(self._history)

    def probe(self, triple) -> Optional[bool]:
        """Submit a test case [x, y, z]; return the hidden rule's boolean.
        Returns None and records nothing if the input is malformed or budget is
        spent (the agent should check remaining())."""
        if self.remaining() <= 0:
            raise ProbeExhausted("no probes remaining")
        if not (isinstance(triple, (list, tuple)) and len(triple) == 3 and all(_valid_number(v) for v in triple)):
            # Malformed probe: record as a wasted turn (label False) so the agent
            # is not rewarded for emitting garbage, mirroring a real harness.
            self._history.append({"triple": None, "label": False, "reused": False, "malformed": True})
            return False
        triple = [float(v) if isinstance(v, float) else int(v) for v in triple]
        key = tuple(triple)
        reused = key in self._seen
        self._seen.add(key)
        try:
            label = bool(self._hidden(*triple))
        except Exception:
            label = False
        self._history.append({"triple": triple, "label": label, "reused": reused, "malformed": False})
        return label

    def history(self) -> List[dict]:
        return list(self._history)

    def used(self) -> int:
        return len(self._history)
